"""Generate a Base/EVM key locally. The private file is gitignored and chmod 0600."""
from pathlib import Path
import os
import secrets

P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
RC = [1,0x8082,0x800000000000808A,0x8000000080008000,0x808B,0x80000001,
      0x8000000080008081,0x8000000000008009,0x8A,0x88,0x80008009,0x8000000A,
      0x8000808B,0x800000000000008B,0x8000000000008089,0x8000000000008003,
      0x8000000000008002,0x8000000000000080,0x800A,0x800000008000000A,
      0x8000000080008081,0x8000000000008080,0x80000001,0x8000000080008008]
ROT = [[0,36,3,41,18],[1,44,10,45,2],[62,6,43,15,61],
       [28,55,25,21,56],[27,20,39,8,14]]
MASK = (1 << 64) - 1

def add(a, b):
    if a is None: return b
    if b is None: return a
    if a == b:
        slope = (3*a[0]*a[0]) * pow(2*a[1], P-2, P) % P
    else:
        slope = (b[1]-a[1]) * pow((b[0]-a[0]) % P, P-2, P) % P
    x = (slope*slope-a[0]-b[0]) % P
    return x, (slope*(a[0]-x)-a[1]) % P

def multiply(k, point=G):
    result = None
    while k:
        if k & 1: result = add(result, point)
        point = add(point, point); k >>= 1
    return result

def rol(v, n): return ((v << n) | (v >> (64-n))) & MASK if n else v

def keccak256(data):
    rate=136; padded=bytearray(data); padded.append(1)
    padded.extend(b'\0' * ((rate-1-len(padded)) % rate)); padded.append(0x80)
    state=[0]*25
    for off in range(0,len(padded),rate):
        block=padded[off:off+rate]
        for i in range(rate//8): state[i] ^= int.from_bytes(block[8*i:8*i+8],'little')
        for rc in RC:
            c=[state[x]^state[x+5]^state[x+10]^state[x+15]^state[x+20] for x in range(5)]
            d=[c[(x-1)%5]^rol(c[(x+1)%5],1) for x in range(5)]
            for x in range(5):
                for y in range(5): state[x+5*y]^=d[x]
            b=[0]*25
            for x in range(5):
                for y in range(5): b[y+5*((2*x+3*y)%5)]=rol(state[x+5*y],ROT[x][y])
            for x in range(5):
                for y in range(5): state[x+5*y]=b[x+5*y]^((~b[(x+1)%5+5*y])&b[(x+2)%5+5*y])
            state[0]^=rc
    return b''.join(x.to_bytes(8,'little') for x in state)[:32]

def checksum(raw):
    lower=raw.hex(); digest=keccak256(lower.encode()).hex()
    return '0x'+''.join(c.upper() if c in 'abcdef' and int(digest[i],16)>=8 else c for i,c in enumerate(lower))

def main():
    private=secrets.randbelow(N-1)+1; public=multiply(private)
    encoded=public[0].to_bytes(32,'big')+public[1].to_bytes(32,'big')
    address=checksum(keccak256(encoded)[-20:])
    root=Path(__file__).resolve().parents[1]/'.private'; root.mkdir(mode=0o700,exist_ok=True)
    key=root/'mainnet-deployer.key'; key.write_text(f'{private:064x}\n'); os.chmod(key,0o600)
    (root/'mainnet-deployer.address').write_text(address+'\n')
    print(address)

if __name__ == '__main__': main()
