"""Binary convention only: bit zero is bottom line; no numbering maps implied."""


def validate(code):
    if type(code) is not int or not 0 <= code < 64:
        raise ValueError("hexagram code must be an integer 0..63")
    return code


def lines(code):
    return [(validate(code) >> i) & 1 for i in range(6)]


def encode(values):
    if len(values) != 6 or any(type(v) is not int or v not in (0, 1) for v in values):
        raise ValueError("six binary lines required")
    return sum(v << i for i, v in enumerate(values))


def flip(code, positions):
    validate(code)
    if len(set(positions)) != len(positions) or any(type(i) is not int or not 1 <= i <= 6 for i in positions):
        raise ValueError("unique line positions 1..6 required")
    return code ^ sum(1 << (i - 1) for i in positions)


def complement(code):
    return validate(code) ^ 63


def reverse(code):
    return encode(lines(code)[::-1])


def exchange_trigrams(code):
    values = lines(code)
    return encode(values[3:] + values[:3])


def nuclear(code):
    values = lines(code)
    return encode([values[i - 1] for i in (2, 3, 4, 3, 4, 5)])
