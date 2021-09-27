import csv
import sys
import re
from collections import Counter

if len(sys.argv) != 3:
    print("Usage: python dna.py data.csv sequence.txt")

database = open(sys.argv[1], "r")
reader = csv.reader(database)
people = {}
if sys.argv[1] == 'databases/small.csv':
    small = True
    large = False
    for row in reader:
        people[row[0]] = {'AGATC': row[1], 'AATG': row[2], 'TATC': row[3]}
else:
    large = True
    small = False
    for row in reader:
        people[row[0]] = {'AGATC': row[1], 'TTTTTTCT': row[2], 'AATG': row[3],
                          'TCTAG': row[4], 'GATA': row[5], 'TATC': row[6], 'GAAA': row[7], 'TCTG': row[8]}

sequence = open(sys.argv[2], "r")
sequence = sequence.read()
matches = []
matches1 = 0
for value in people['name']:
    substring = people['name'][value]
    counter = 1
    repetition = 2
    while True:
        if (substring * repetition) in sequence:
            counter += 1
            repetition += 1
        else:
            break
    counter = str(counter)

    for key in people:
        if people[key][substring] == counter:
            voted = key
            matches.append(voted)
            matches1 += 1

check_matches = Counter(matches)
if large == True:
    if check_matches.most_common(1)[0][1] < 8:
        print("No match")
    else:
        print(check_matches.most_common(1)[0][0])
if small == True:
    if check_matches.most_common(1)[0][1] < 3:
        print("No match")
    else:
        print(check_matches.most_common(1)[0][0])