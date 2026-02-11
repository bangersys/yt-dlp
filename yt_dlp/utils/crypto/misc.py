def caesar(s, alphabet, shift):
    if shift == 0:
        return s
    l = len(alphabet)
    return ''.join(
        alphabet[(alphabet.index(c) + shift) % l] if c in alphabet else c
        for c in s)


def rot47(s):
    return caesar(s, r'''!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~''', 47)


def urshift(val, n):
    return val >> n if val >= 0 else (val + 0x100000000) >> n
