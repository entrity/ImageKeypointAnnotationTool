awk '{print gsub(/,/,"")}' ${1:-output.txt}
