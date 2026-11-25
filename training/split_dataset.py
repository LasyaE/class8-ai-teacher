import json
import random
import sys

def split_dataset(input_path, train_path, test_path, validate_path, test_size=0.2, validate_size=0.2):
    with open(input_path, 'r') as infile:
        records = [json.loads(line) for line in infile]
    random.seed(42)
    random.shuffle(records)
    
    test_split = int(len(records) * test_size)
    validate_split = int(len(records) * validate_size)
    
    with open(train_path, 'w') as train_file, open(test_path, 'w') as test_file, open(validate_path, 'w') as validate_file:
        for record in records[:validate_split]:
            validate_file.write(json.dumps(record) + '\n')
        for record in records[validate_split:validate_split+test_split]:
            test_file.write(json.dumps(record) + '\n')
        for record in records[validate_split+test_split:]:
            train_file.write(json,record) + '\n')

if __name__ == '__main__':
    split_dataset(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])