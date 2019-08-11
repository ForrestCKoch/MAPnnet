#!/bin/sh

for i in 1-1-1-1-1_1-1-1-1-2 1-1-1-2-2_1-1-2-2-2 1-2-2-2-2_2-2-2-2-2 2-2-2-2-3_2-2-2-3-3 2-2-3-3-3_2-3-3-3-3 3-3-3-3-3_2-2-2-2-4 2-2-2-4-4_2-2-4-4-4 2-1-1-1-1_1-1-1-1-1 2-2-2-1-1_2-2-1-1-1 2-2-2-2-2_2-2-2-2-1 3-3-2-2-2_3-2-2-2-2 3-3-3-3-2_3-3-3-2-2 4-2-2-2-2_3-3-3-3-3 4-4-4-2-2_4-4-2-2-2 1-1-1-1-2_2-1-1-1-1 1-1-1-2-2_2-2-1-1-1 1-1-2-2-2_2-2-2-1-1 1-2-2-2-2_2-2-2-2-1 2-2-2-2-3_3-2-2-2-2 2-2-2-3-3_3-3-2-2-2 2-2-3-3-3_3-3-3-2-2 2-3-3-3-3_3-3-3-3-2 2-2-2-2-4_4-2-2-2-2 2-2-2-4-4_4-4-2-2-2 2-2-4-4-4_4-4-4-2-2 2-4-4-4-4_4-4-4-4-2 1-1-1-1-1_2-2-2-2-2 3-3-3-3-3_4-4-4-4-4; do
    echo $i
    f1=$(echo $i|cut -d'_' -f1)
    f2=$(echo $i|cut -d'_' -f2)
    d1="$f1"
    d2="$f2"
    o1="logs/fixed-filters_test/$d1"
    o2="logs/fixed-filters_test/$d2"
    m1="models/fixed-filters_test/$d1"
    m2="models/fixed-filters_test/$d2"
    l1="$o1-log.txt"
    l2="$o2-log.txt"
    qsub -o logs/jobs/fixed-filters_test-${i}.log -e logs/jobs/fixed-filters_test2-${i}.err -v filters1=$f1,filters2=$f2,outdir1=$m1,outdir2=$m2,log1=$l1,log2=$l2 scripts/raijin_filter_test2.sh

done
