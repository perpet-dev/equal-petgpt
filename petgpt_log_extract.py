#-*- coding:utf-8 -*- 
#!/usr/bin/env python
# by Albert 
import sys
if len(sys.argv) != 2: print("Usage: python3 petgpt_log_extract.py")
else:
    with open(sys.argv[1], 'r', encoding='utf-8') as infile:
        for line in infile:
            idx = line.strip().find("PETGPT_LOG")
            if idx > 0: print(line.strip()[idx+11:])