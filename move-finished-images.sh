#!/bin/bash

outfile=${1:-output.txt}

while read f; do
	mv -n "$f" 'done-inputs/'
done < <(grep .jpg $outfile)

idx=$( ls *output.txt|wc -l )
mv -n "$outfile" "${idx}-output.txt"
