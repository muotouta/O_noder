def num_to_alpha_col(num: int) -> str:
    """
    整数numをExcel風のアルファベット列名に変換する関数
    例: 1->A, 26->Z, 27->AA, 52->AZ, 53->BA ...
    """
    if num <= 0:
        raise ValueError("1以上の整数を指定してください")

    result = ""
    while num > 0:
        num -= 1  # 1始まり(1-26)を0始まり(0-25)に補正して計算しやすくする
        remainder = num % 26
        
        # chr(65) は 'A' です。remainder(0~25) を足して文字に変換します。
        # 先頭に追加していくことで桁上がりを表現します。
        result = chr(65 + remainder) + result
        
        num //= 26  # 次の桁へ

    return result

# --- 動作確認用 ---
if __name__ == "__main__":
    test_cases = [1, 5, 26, 27, 52, 53, 702, 703, 16384]
    for n in test_cases:
        print(f"{n} -> {num_to_alpha_col(n)}")
