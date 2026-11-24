"""Runtime for the two small trained models (router / capability sorter): a 26M encoder-decoder ("needle"), forward pass in numpy only.
Optional feature: without numpy or without the weight files everything returns None and the rule-based code stays in charge.
It does not generate text: it scores the few allowed answers (teacher forced log-likelihood) and returns the best label. No JAX, no sentencepiece."""
import heapq
import math
import os
import struct

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")      # numpy is first imported by Needle; on a busy machine 16 BLAS threads made one request take 3 s instead of ~50 ms
os.environ.setdefault("OMP_NUM_THREADS", "2")
D, H, KV, HD, EL, DL = 512, 8, 4, 64, 12, 8
EOS, TOOL_CALL, TOOLS = 1, 4, 5
MAX_ENC = 256
_ATTN = (("q_proj", "q_proj/kernel"), ("k_proj", "k_proj/kernel"), ("v_proj", "v_proj/kernel"), ("out_proj", "out_proj/kernel"), ("q_norm", "q_norm/scale"), ("k_norm", "k_norm/scale"))


# ---------------- tokenizer: sentencepiece BPE (identity normaliser, dummy prefix, byte fallback), read from the .model protobuf ----------------
def _varint(b, i):
    r = s = 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        if c < 0x80:
            return r, i
        s += 7


def _piece(blob, j, end):
    piece, score, typ = "", 0.0, 1
    while j < end:
        t, j = _varint(blob, j)
        f, w = t >> 3, t & 7
        if w == 2:
            n, j = _varint(blob, j)
            if f == 1:
                piece = blob[j:j + n].decode("utf-8", "replace")
            j += n
        elif w == 5:
            if f == 2:
                score = struct.unpack("<f", blob[j:j + 4])[0]
            j += 4
        elif w == 0:
            v, j = _varint(blob, j)
            if f == 3:
                typ = v
        else:
            j += 8
    return piece, score, typ


def _pieces(blob):
    out, i = [], 0
    while i < len(blob):
        t, i = _varint(blob, i)
        f, w = t >> 3, t & 7
        if w == 0:
            _, i = _varint(blob, i)
        elif w == 1:
            i += 8
        elif w == 5:
            i += 4
        else:
            n, i = _varint(blob, i)
            if f == 1:
                out.append(_piece(blob, i, i + n))
            i += n
    return out


class Tok:
    def __init__(self, path):
        with open(path, "rb") as f:
            ps = _pieces(f.read())
        self.id = {p: k for k, (p, _s, t) in enumerate(ps) if t in (1, 4)}          # normal + user defined
        self.score = {p: s for p, s, t in ps if t == 1}
        self.byte = {int(p[3:5], 16): k for k, (p, _s, t) in enumerate(ps) if t == 6 and p.startswith("<0x")}
        self._cache = {}

    def encode(self, text):
        """BPE with a heap: merge the adjacent pair with the best score first (leftmost wins ties). O(n log n); results of short texts are cached"""
        if text in self._cache:
            return list(self._cache[text])
        t = text.strip(" ")
        t = "▁" + "▁".join(x for x in t.split(" ") if x) if t else ""                 # only plain spaces are whitespace; \n etc. stay and fall back to bytes
        syms = list(t)
        n = len(syms)
        prv, nxt, sc = list(range(-1, n - 1)), list(range(1, n + 1)), self.score
        heap = []

        def push(i):
            j = nxt[i]
            if 0 <= i and j < n:
                s = sc.get(syms[i] + syms[j])
                if s is not None:
                    heapq.heappush(heap, (-s, i, syms[i] + syms[j]))
        for i in range(n - 1):
            push(i)
        while heap:
            _s, i, m = heapq.heappop(heap)
            j = nxt[i] if syms[i] is not None else n
            if syms[i] is None or j >= n or syms[j] is None or syms[i] + syms[j] != m:        # stale entry
                continue
            syms[i], syms[j] = m, None
            nxt[i] = nxt[j]
            if nxt[j] < n:
                prv[nxt[j]] = i
            if prv[i] >= 0:
                push(prv[i])
            push(i)
        ids = []
        for s in syms:
            if s is not None:
                ids += [self.id[s]] if s in self.id else [self.byte.get(b, 3) for b in s.encode("utf-8")]
        if len(text) < 400 and len(self._cache) < 512:
            self._cache[text] = tuple(ids)
        return ids


# ---------------- model ----------------
class Needle:
    def __init__(self, weights, tokenizer):
        import numpy as np
        self.np = np
        z = np.load(weights)
        self.w = {k: (z[k].astype(np.uint32) << 16).view(np.float32) if z[k].dtype == np.uint16 else z[k].astype(np.float32) for k in z.files}   # bf16 stored as raw uint16
        self.emb = self.w["embedding/embedding"]
        self.embT = np.ascontiguousarray(self.emb.T)
        self.tok = Tok(tokenizer)
        ang = np.outer(np.arange(1024, dtype=np.float32), 1.0 / (10000.0 ** (np.arange(0, HD, 2, dtype=np.float32) / HD)))
        self.cos, self.sin = np.cos(ang).astype(np.float32), np.sin(ang).astype(np.float32)
        self.sg = {k: 1 / (1 + np.exp(-v)) for k, v in self.w.items() if k.endswith("_gate")}
        self.ans_ids = {}

    def _norm(self, x, scale):
        return (1 + scale) * x / self.np.sqrt(self.np.mean(x * x, axis=-1, keepdims=True) + 1e-6)

    def _rope(self, x):                                         # x (B, heads, T, HD), rotate halves
        T, h = x.shape[2], HD // 2
        c, s = self.cos[:T], self.sin[:T]
        return self.np.concatenate([x[..., :h] * c - x[..., h:] * s, x[..., h:] * c + x[..., :h] * s], axis=-1)

    def _kv(self, p, kv_in, rope):                              # (B, T, D) -> k, v as (B, H, T, HD)
        np = self.np
        B, Tk = kv_in.shape[:2]
        k = (kv_in @ p["k_proj"]).reshape(B, Tk, KV, HD).transpose(0, 2, 1, 3)
        v = (kv_in @ p["v_proj"]).reshape(B, Tk, KV, HD).transpose(0, 2, 1, 3)
        k = self._norm(k, p["k_norm"])
        k, v = np.repeat(k, H // KV, axis=1), np.repeat(v, H // KV, axis=1)
        return (self._rope(k) if rope else k), v

    def _attn(self, p, q_in, kv, causal, rope):                 # q_in (B, Tq, D), kv = (k, v)
        np = self.np
        B, Tq = q_in.shape[:2]
        k, v = kv
        q = self._norm((q_in @ p["q_proj"]).reshape(B, Tq, H, HD).transpose(0, 2, 1, 3), p["q_norm"])
        if rope:
            q = self._rope(q)
        a = q @ k.transpose(0, 1, 3, 2) / 8.0
        if causal:
            a = np.where(np.tril(np.ones((Tq, k.shape[2]), bool))[None, None], a, -1e30)
        a = np.exp(a - a.max(-1, keepdims=True))
        a /= a.sum(-1, keepdims=True)
        return (a @ v).transpose(0, 2, 1, 3).reshape(B, Tq, D) @ p["out_proj"]

    def _p(self, base, l):
        return {n: self.w[base + k][l] for n, k in _ATTN}

    def encode(self, ids):
        w, e = self.w, "encoder/layers/EncoderBlock_0/"
        x = (self.emb[ids] * math.sqrt(D))[None]
        for l in range(EL):
            p = self._p(e + "self_attn/", l)
            h = self._norm(x, w[e + "ZCRMSNorm_0/scale"][l])
            x = x + self.sg[e + "attn_gate"][l] * self._attn(p, h, self._kv(p, h, True), False, True)
        return self._norm(x, w["encoder/final_norm/scale"])

    def cross_kv(self, enc):
        d = "decoder/layers/DecoderBlock_0/"
        return [self._kv(self._p(d + "cross_attn/", l), enc, False) for l in range(DL)]

    def decode_hidden(self, ckv, dec_ids):
        """dec_ids (B, T) -> final normed hidden states (B, T, D); ckv = cross_kv(enc), shared by the whole batch"""
        w, d = self.w, "decoder/layers/DecoderBlock_0/"
        x = self.emb[dec_ids] * math.sqrt(D)
        for l in range(DL):
            ps, pc = self._p(d + "self_attn/", l), self._p(d + "cross_attn/", l)
            h = self._norm(x, w[d + "ZCRMSNorm_0/scale"][l])
            x = x + self.sg[d + "self_attn_gate"][l] * self._attn(ps, h, self._kv(ps, h, True), True, True)
            h = self._norm(x, w[d + "ZCRMSNorm_1/scale"][l])
            x = x + self.sg[d + "cross_attn_gate"][l] * self._attn(pc, h, ckv[l], False, False)
        return self._norm(x, w["decoder/ZCRMSNorm_0/scale"])

    def _ans(self, a):
        if a not in self.ans_ids:
            self.ans_ids[a] = [TOOL_CALL] + self.tok.encode(a) + [EOS]
        return self.ans_ids[a]

    def score(self, query, tools_json, answers):
        """answers {label: answer text exactly as trained} -> {label: log-probability of [<tool_call>, answer tokens, EOS], summed only from the first position where the candidates differ
        (the shared prefix is the same term for every candidate and cannot change the ranking)"""
        np = self.np
        q = self.tok.encode(query[:2000])[:MAX_ENC - 2]
        t = self.tok.encode(tools_json)[:MAX_ENC - len(q) - 1]
        ckv = self.cross_kv(self.encode(np.array(q + [TOOLS] + t)))
        labs = list(answers)
        tg = [self._ans(answers[l]) for l in labs]
        L = max(len(x) for x in tg)
        s0 = 0
        if len(tg) > 1:
            s0 = min((next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b))) for a in tg for b in tg if a is not b), default=0)
        pad = [x + [EOS] * (L - len(x)) for x in tg]
        hid = self.decode_hidden(ckv, np.array([[EOS] + x[:-1] for x in pad]))[:, s0:]
        lg = hid @ self.embT
        lg = lg - lg.max(-1, keepdims=True)
        lp = lg - np.log(np.exp(lg).sum(-1, keepdims=True))
        return {l: float(sum(lp[b, i - s0, tok] for i, tok in enumerate(x) if i >= s0)) for b, (l, x) in enumerate(zip(labs, tg))}
