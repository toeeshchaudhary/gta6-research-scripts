import json, os, hashlib, struct, sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(BASE, 'work', 'manifest', 'out')

def joaat(s):
    h = 0
    for b in s.encode('utf-8', 'ignore'):
        h = (h + b) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h

def joaat64(s):
    h = 0
    M = (1 << 64) - 1
    for b in s.encode('utf-8', 'ignore'):
        h = (h + b) & M
        h = (h + (h << 10)) & M
        h ^= h >> 6
    h = (h + (h << 3)) & M
    h ^= h >> 11
    h = (h + (h << 15)) & M
    return h

def fnv1a64(s):
    h = 0xcbf29ce484222325
    for b in s.encode('utf-8', 'ignore'):
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def fnv1a32(s):
    h = 0x811c9dc5
    for b in s.encode('utf-8', 'ignore'):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h
