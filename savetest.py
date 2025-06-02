import os
import sys
import time
import pypmx

def binary_compare(file1, file2):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        chunk_size = 64
        pos = 0
        while True:
            b1 = f1.read(chunk_size)
            b2 = f2.read(chunk_size)
            if b1 != b2:
                return pos, b1, b2  # 異なる位置（バイトオフセット） と差分を返す
            if not b1:
                break
            pos += chunk_size
    return -1, 0, 0  # 完全一致

def binary_compare_reversed(file1, file2): # from end
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        chunk_size = 64
        f1.seek(0, os.SEEK_END)
        f2.seek(0, os.SEEK_END)
        pos = 0
        while True:
            f1.seek(-chunk_size - pos, os.SEEK_END)
            f2.seek(-chunk_size - pos, os.SEEK_END)
            b1 = f1.read(chunk_size)
            b2 = f2.read(chunk_size)
            if b1 != b2:
                return pos, b1, b2  # 異なる位置（バイトオフセット） と差分を返す
            if not b1:
                break
            pos += chunk_size
    return -1, 0, 0  # 完全一致

def size_difference(file1, file2):
    size1 = os.path.getsize(file1)
    size2 = os.path.getsize(file2)
    if size1 != size2:
        return size2 - size1
    
    return 0


def test_roundtrip(pmx_path):
    if not os.path.isfile(pmx_path):
        print(f"❌ ファイルが存在しません: {pmx_path}")
        return

    start_time = time.time()
    print(f"📂 ロード中: {pmx_path}")
    try:
        model = pypmx.load(pmx_path)
    except Exception as e:
        print(f"❌ ロード失敗: {e}")
        raise

    time_taken_ms = (time.time() - start_time) * 1000
    print(f"✅ ロード成功: {time_taken_ms:.2f} ms")


    output_path = pmx_path + ".out.pmx"

    start_time = time.time()
    print(f"📂 セーブ中: {output_path}")

    try:
        pypmx.save(output_path, model)
    except Exception as e:
        print(f"❌ セーブ失敗: {e}")
        raise

    time_taken_ms = (time.time() - start_time) * 1000
    print(f"✅ セーブ成功: {time_taken_ms:.2f} ms")

    diff_pos, b1, b2 = binary_compare(pmx_path, output_path)
    diff_size = size_difference(pmx_path, output_path)

    if diff_pos == -1:
        print("✅ バイナリ一致: セーブ前後で差分はありません。")
    else:
        print(f"⚠ 差分あり: 最初の差は先頭から {diff_pos} バイト目にあります。(末尾からのバイト数: {os.path.getsize(pmx_path) - diff_pos} 割合: {diff_pos / os.path.getsize(pmx_path) * 100:.2f}%)")
        print(f"   元: {list(b1)}")
        print(f"   後: {list(b2)}")

        ascii_prev = [chr(b) if 32 <= b < 127 else '.' for b in b1]
        ascii_new = [chr(b) if 32 <= b < 127 else '.' for b in b2]
        print(f"   元 (ASCII): {''.join(c for c in ascii_prev)}")
        print(f"   後 (ASCII): {''.join(c for c in ascii_new)}")

        print(f"   サイズ差: {diff_size} バイト")
        print(f"   セーブ前: {os.path.getsize(pmx_path)} バイト")
        print(f"   セーブ後: {os.path.getsize(output_path)} バイト")

        print("末尾から比較")
        diff_pos_rev, b1_rev, b2_rev = binary_compare_reversed(pmx_path, output_path)
        print(f"⚠ 末尾からの差分あり: 最初の差は末尾から {diff_pos_rev} バイト目にあります。(先頭からのバイト数: {os.path.getsize(pmx_path) - diff_pos_rev} 割合: {diff_pos_rev / os.path.getsize(pmx_path) * 100:.2f}%)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        input_file = "test.pmx"
    else:
        input_file = sys.argv[1]

    if not os.path.isfile(input_file) or not input_file.lower().endswith(".pmx"):
        print("❌ 入力ファイルがPMX形式ではないか、存在しません。")
        sys.exit()

    test_roundtrip(input_file)
