import json
import sys

def validate_record(record):
    try:
        if not record.get('source') or not record.get('chapter') or not record.get('page'):
            return False
        if not isinstance(record.get('content'), str):
            return False
        return True
    except:
        return False

def main():
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            record = json.loads(line)
            if validate_record(record):
                outfile.write(json.dumps(record) + '\n')

if __name__ == '__main__':
    main()