
import sys

def read_chunk(filepath, start_line, num_lines):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= start_line:
                print(f"{i+1}: {line}", end='')
                if i >= start_line + num_lines:
                    break

if __name__ == "__main__":
    read_chunk(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
