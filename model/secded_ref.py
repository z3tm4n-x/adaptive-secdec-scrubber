from itertools import combinations
import random


PARITY_POSITIONS = (1, 2, 4, 8, 16, 32)
OVERALL_PARITY_POSITION = 39

DATA_POSITIONS = tuple(
    position
    for position in range(1, OVERALL_PARITY_POSITION)
    if position not in PARITY_POSITIONS
)

DATA_WIDTH = 32
CODEWORD_WIDTH = 39


def get_bit(value: int, position: int) -> int:
    """Возвращает бит из позиции 1..39."""
    return (value >> (position - 1)) & 1


def set_bit(value: int, position: int, bit: int) -> int:
    """Устанавливает бит в позиции 1..39."""
    mask = 1 << (position - 1)

    if bit:
        return value | mask

    return value & ~mask


def flip_bit(value: int, position: int) -> int:
    """Инвертирует бит в позиции 1..39."""
    return value ^ (1 << (position - 1))


def extract_data(codeword: int) -> int:
    """Извлекает 32 информационных бита из 39-битного кодового слова."""
    data = 0

    for data_index, code_position in enumerate(DATA_POSITIONS):
        if get_bit(codeword, code_position):
            data |= 1 << data_index

    return data


def encode(data: int) -> int:
    """
    Кодирует 32-битное слово данных в 39-битное SECDED-кодовое слово.

    Позиции:
    1, 2, 4, 8, 16, 32 — проверочные биты Хэмминга.
    39 — общий бит чётности.
    Остальные позиции — информационные биты.
    """
    if not (0 <= data < (1 << DATA_WIDTH)):
        raise ValueError("data must be a 32-bit unsigned integer")

    codeword = 0

    # Размещение информационных битов.
    for data_index, code_position in enumerate(DATA_POSITIONS):
        bit = (data >> data_index) & 1
        codeword = set_bit(codeword, code_position, bit)

    # Вычисление проверочных битов Хэмминга.
    for parity_position in PARITY_POSITIONS:
        parity = 0

        for code_position in range(1, OVERALL_PARITY_POSITION):
            if code_position & parity_position:
                if code_position != parity_position:
                    parity ^= get_bit(codeword, code_position)

        codeword = set_bit(codeword, parity_position, parity)

    # Общий бит чётности.
    overall_parity = 0
    for code_position in range(1, OVERALL_PARITY_POSITION):
        overall_parity ^= get_bit(codeword, code_position)

    codeword = set_bit(codeword, OVERALL_PARITY_POSITION, overall_parity)

    return codeword


def calculate_syndrome(codeword: int) -> int:
    """Вычисляет синдром по первым 38 позициям кодового слова."""
    syndrome = 0

    for parity_position in PARITY_POSITIONS:
        parity = 0

        for code_position in range(1, OVERALL_PARITY_POSITION):
            if code_position & parity_position:
                parity ^= get_bit(codeword, code_position)

        if parity:
            syndrome |= parity_position

    return syndrome


def calculate_overall_parity(codeword: int) -> int:
    """Вычисляет общую чётность всего 39-битного слова."""
    parity = 0

    for code_position in range(1, CODEWORD_WIDTH + 1):
        parity ^= get_bit(codeword, code_position)

    return parity


def decode(codeword: int) -> dict:
    """
    Декодирует 39-битное SECDED-кодовое слово.

    Возвращает словарь:
    - corrected_codeword;
    - data;
    - syndrome;
    - overall_parity_error;
    - single_error;
    - double_error;
    - uncorrectable;
    - error_position.
    """
    if not (0 <= codeword < (1 << CODEWORD_WIDTH)):
        raise ValueError("codeword must be a 39-bit unsigned integer")

    syndrome = calculate_syndrome(codeword)
    overall_parity_error = calculate_overall_parity(codeword)

    corrected_codeword = codeword
    single_error = False
    double_error = False
    uncorrectable = False
    error_position = 0

    if syndrome == 0 and overall_parity_error == 0:
        # Ошибки нет.
        pass

    elif syndrome != 0 and overall_parity_error == 1:
        # Одиночная ошибка в одной из позиций 1..38.
        if 1 <= syndrome <= 38:
            corrected_codeword = flip_bit(codeword, syndrome)
            single_error = True
            error_position = syndrome
        else:
            # Для одиночной ошибки в рассматриваемом коде такого быть не должно.
            uncorrectable = True

    elif syndrome == 0 and overall_parity_error == 1:
        # Одиночная ошибка в общем бите чётности.
        corrected_codeword = flip_bit(codeword, OVERALL_PARITY_POSITION)
        single_error = True
        error_position = OVERALL_PARITY_POSITION

    else:
        # syndrome != 0 and overall_parity_error == 0
        # Двойная ошибка: обнаруживается, но не исправляется.
        double_error = True
        uncorrectable = True

    data = extract_data(corrected_codeword)

    return {
        "corrected_codeword": corrected_codeword,
        "data": data,
        "syndrome": syndrome,
        "overall_parity_error": overall_parity_error,
        "single_error": single_error,
        "double_error": double_error,
        "uncorrectable": uncorrectable,
        "error_position": error_position,
    }


def self_check() -> None:
    """Проверяет модель SECDED на одиночных и двойных ошибках."""
    print("SECDED 32+7 reference model")
    print(f"Data positions: {DATA_POSITIONS}")
    print(f"Parity positions: {PARITY_POSITIONS}")
    print(f"Overall parity position: {OVERALL_PARITY_POSITION}")

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

    for data in test_values:
        codeword = encode(data)

        # Проверка отсутствия ошибки.
        result = decode(codeword)
        assert result["data"] == data
        assert result["corrected_codeword"] == codeword
        assert not result["single_error"]
        assert not result["double_error"]
        assert not result["uncorrectable"]
        assert result["error_position"] == 0

        # Проверка всех одиночных ошибок.
        for error_position in range(1, CODEWORD_WIDTH + 1):
            corrupted = flip_bit(codeword, error_position)
            result = decode(corrupted)

            assert result["single_error"]
            assert not result["double_error"]
            assert not result["uncorrectable"]
            assert result["error_position"] == error_position
            assert result["corrected_codeword"] == codeword
            assert result["data"] == data

        # Проверка всех двойных ошибок.
        for pos_a, pos_b in combinations(range(1, CODEWORD_WIDTH + 1), 2):
            corrupted = flip_bit(flip_bit(codeword, pos_a), pos_b)
            result = decode(corrupted)

            assert not result["single_error"]
            assert result["double_error"]
            assert result["uncorrectable"]

    print(f"Checked data words: {len(test_values)}")
    print("All SECDED checks passed.")


if __name__ == "__main__":
    self_check()