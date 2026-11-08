import numpy as np


class MLP:
    architecture_type = "tiny-mlp-v1"
    input_size = 8
    hidden_size = 12
    output_size = 2
    macs = input_size * hidden_size + hidden_size * output_size

    def __init__(self, seed=0):
        self.initialize(seed)

    def initialize(self, seed=0):
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0, .2, (8, 12))
        self.b1 = np.zeros(12)
        self.w2 = rng.normal(0, .2, (12, 2))
        self.b2 = np.zeros(2)

    def forward(self, inputs, state=None):
        x = np.asarray(inputs, dtype=np.float64)
        if x.shape != (8,) or not np.isfinite(x).all():
            raise ValueError("eight finite neural features required")
        if state is not None:
            x = x + np.asarray(state, dtype=np.float64)
        h = np.tanh(x @ self.w1 + self.b1)
        z = h @ self.w2 + self.b2
        p = np.exp(z - z.max())
        return p / p.sum()

    def update(self, inputs, target, rate=.05):
        if type(target) is not int or target not in (0, 1):
            raise ValueError("binary verified target required")
        x = np.asarray(inputs, dtype=np.float64)
        p = self.forward(x)
        h = np.tanh(x @ self.w1 + self.b1)
        dz = p.copy()
        dz[target] -= 1
        dh = (dz @ self.w2.T) * (1 - h * h)
        self.w2 -= rate * np.outer(h, dz)
        self.b2 -= rate * dz
        self.w1 -= rate * np.outer(x, dh)
        self.b1 -= rate * dh
        return float(-np.log(max(float(p[target]), 1e-15)))

    def snapshot(self):
        return {k: getattr(self, k).tolist() for k in ("w1", "b1", "w2", "b2")}

    def restore(self, value):
        for name, shape in (("w1", (8, 12)), ("b1", (12,)), ("w2", (12, 2)), ("b2", (2,))):
            array = np.asarray(value[name], dtype=np.float64)
            if array.shape != shape or not np.isfinite(array).all():
                raise ValueError("invalid model checkpoint")
            setattr(self, name, array.copy())
