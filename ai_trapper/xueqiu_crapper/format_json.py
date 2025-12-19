import json
from pathlib import Path
import argparse


def format_json_file(input_file: Path, output_file: Path = None):
    """
    将单行JSON文件转换为格式化的多行JSON文件
    """
    if not input_file.exists():
        print(f"文件 {input_file} 不存在")
        return
    
    if output_file is None:
        output_file = input_file.with_name(f"formatted_{input_file.name}")
    
    formatted_records = []
    
    # 读取原始文件
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                formatted_records.append(record)
            except json.JSONDecodeError as e:
                print(f"第 {line_num} 行解析错误: {e}")
                continue
    
    # 写入格式化的文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in formatted_records:
            f.write(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    
    print(f"已将 {len(formatted_records)} 条记录保存到 {output_file}")


def format_all_json_files(directory: Path):
    """
    格式化目录中的所有JSONL文件
    """
    if not directory.exists():
        print(f"目录 {directory} 不存在")
        return
    
    json_files = list(directory.glob("*.jsonl"))
    if not json_files:
        print(f"目录 {directory} 中没有找到JSONL文件")
        return
    
    for json_file in json_files:
        print(f"正在处理 {json_file}...")
        output_file = json_file.with_name(f"formatted_{json_file.name}")
        format_json_file(json_file, output_file)


def main():
    parser = argparse.ArgumentParser(description="格式化JSONL文件")
    parser.add_argument("--input", "-i", help="输入文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--directory", "-d", help="处理整个目录中的JSONL文件")
    args = parser.parse_args()
    
    if args.directory:
        format_all_json_files(Path(args.directory))
    elif args.input:
        input_file = Path(args.input)
        output_file = Path(args.output) if args.output else None
        format_json_file(input_file, output_file)
    else:
        print("请指定输入文件或目录")


if __name__ == "__main__":
    main()