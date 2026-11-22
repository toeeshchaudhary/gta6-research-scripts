# Extract the M2 game-shader pair (SPIR-V + FSSM + DXBC input/output signatures)
# into engine\shaders\gs\ and write META.json describing the chosen heap VAs.
import base64
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
S2 = os.path.join(ROOT, "work", "spirv_run", "spirv_s2")
SH2 = os.path.join(ROOT, "work", "shaders2")
OUT = os.path.join(ROOT, "engine", "shaders", "gs")

PAIR = [
    ("vs_passthrough", "000005_vs_VS_Passthrough_36b96a91_Wrapped", 0x10000),
    ("ps_passthrough_copy", "011050_ps_PS_PassthroughCopy_1a08fc46_Wrapped", 0x20000),
]

# DXBC chunk parser (ISG1/OSG1 live in the .cso container).
COMPONENT = {1: "u32", 2: "s32", 3: "f32"}
MASK = {1: ".x", 2: ".xy", 3: ".xyz", 7: ".xyz", 15: ".xyzw"}


def chunks(blob):
    if blob[:4] != b"DXBC":
        raise SystemExit("not DXBC")
    # header: magic, hash[16], unknown, total_size, chunk_count, chunk_offset[count]
    total, count = struct.unpack_from("<II", blob, 24)
    offsets = struct.unpack_from("<%dI" % count, blob, 32)
    for off in offsets:
        if off + 8 > min(total, len(blob)):
            continue
        fourcc = blob[off:off + 4].decode("ascii", "replace")
        size = struct.unpack_from("<I", blob, off + 4)[0]
        yield fourcc, blob[off + 8:off + 8 + size]


def parse_sig(data):
    # Signature chunk: u32 count, u32 unknown, then count * 32-byte elements:
    # [1]=name offset, [2]=semantic index, [3]=sysvalue, [4]=component type,
    # [5]=register, [6]=mask | rwmask<<8, [7]=stream. Strings follow the array.
    count = struct.unpack_from("<I", data, 0)[0]
    table = data[8:]
    elems = []
    for i in range(count):
        e = table[i * 32:(i + 1) * 32]
        name_off = struct.unpack_from("<I", e, 4)[0]
        semidx, sysval, comp, reg, maskrw = struct.unpack_from("<IIIII", e, 8)
        name = data[name_off:data.find(b"\0", name_off)].decode("ascii", "replace")
        mask = maskrw & 0xFF
        elems.append({
            "name": name,
            "semantic_index": semidx,
            "sysvalue": sysval,
            "component_type": COMPONENT.get(comp, str(comp)),
            "register": reg,
            "mask": MASK.get(mask, str(mask)),
            "mask_bits": mask,
            "read_write_mask": (maskrw >> 8) & 0xFF,
        })
    return elems


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {"note": "M2 game-shader pair; VAs are offsets inside the BDA heap, heapBase is added by the shader",
            "heap_va_for_tsharp": 0x1000, "shaders": []}

    for label, name, va in PAIR:
        spv_src = os.path.join(S2, name + ".spv")
        fssm_src = os.path.join(SH2, "fssm", name + ".fssm")
        cso_src = os.path.join(SH2, name + ".cso")
        with open(spv_src, "rb") as f:
            spv = f.read()
        with open(fssm_src, "rb") as f:
            fssm = f.read()
        with open(os.path.join(OUT, label + ".spv"), "wb") as f:
            f.write(spv)
        with open(os.path.join(OUT, label + ".fssm"), "wb") as f:
            f.write(fssm)

        entry = {"label": label, "shader_name": name, "code_va": va,
                 "spv_bytes": len(spv), "fssm_bytes": len(fssm),
                 "fssm_sha1_prefix": __import__("hashlib").sha1(fssm).hexdigest()[:16]}
        with open(cso_src, "rb") as f:
            blob = f.read()
        for fourcc, data in chunks(blob):
            if fourcc == "ISG1":
                entry["isg1"] = parse_sig(data)
            elif fourcc == "OSG1":
                entry["osg1"] = parse_sig(data)
            elif fourcc == "PSV0":
                entry["psv0_bytes"] = len(data)
        meta["shaders"].append(entry)
        print(label, name, "spv", len(spv), "fssm", len(fssm), "code_va", hex(va))

    with open(os.path.join(OUT, "META.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)

    # SPIR-V interface dump (locations / builtins actually declared).
    for entry in meta["shaders"]:
        print(json.dumps(entry.get("isg1"), indent=0))
        print(json.dumps(entry.get("osg1"), indent=0))


if __name__ == "__main__":
    main()
