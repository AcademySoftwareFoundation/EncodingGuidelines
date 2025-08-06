#!/bin/bash

for i in $*
do
j=$i.y4m
ffmpeg -i $i -strict -1 $j
done

