import binascii
import random


def ohdave_rsa_encrypt(data, exponent, modulus):
    """
    Implement OHDave's RSA algorithm. See http://www.ohdave.com/rsa/

    Input:
        data: data to encrypt, bytes-like object
        exponent, modulus: parameter e and N of RSA algorithm, both integer
    Output: hex string of encrypted data

    Limitation: supports one block encryption only
    """

    payload = int(binascii.hexlify(data[::-1]), 16)
    encrypted = pow(payload, exponent, modulus)
    return f'{encrypted:x}'


def pkcs1pad(data, length):
    """
    Padding input data with PKCS#1 scheme

    @param {int[]} data        input data
    @param {int}   length      target length
    @returns {int[]}           padded data
    """
    if len(data) > length - 11:
        raise ValueError('Input data too long for PKCS#1 padding')

    pseudo_random = [random.randint(0, 254) for _ in range(length - len(data) - 3)]
    return [0, 2, *pseudo_random, 0, *data]
