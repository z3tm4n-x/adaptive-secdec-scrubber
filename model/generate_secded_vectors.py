import random
from secded_ref import encode


def main() -> None:
    deterministic_values = [
        0x00000000,
        0x00000001,
        0xFFFFFFFF,
        0xAAAAAAAA,
        0x55555555,
        0x12345678,
        0x87654321,
    ]

    rng = random.Random(12345)
    random_values = [rng.getrandbits(32) for _ in range(200)]

    test_values = deterministic_values + random_values

    output_path = "tb/secded_encode_vectors.txt"

    with open(output_path, "w", encoding="utf-8") as file:
        for data in test_values:
            codeword = encode(data)
            file.write(f"{data:08X} {codeword:010X}\n")

    print(f"Generated {len(test_values)} vectors: {output_path}")


if __name__ == "__main__":
    main()