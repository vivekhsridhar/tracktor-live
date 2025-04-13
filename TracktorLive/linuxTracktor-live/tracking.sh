#!/bin/bash

#Square zone
#~ acm=$(printf /dev/ttyACM*)
acm=$(printf /dev/ttyUSB*)
stty -F "$acm" -hupcl
while IFS=, read -r a b var_1 var_2 < <(tail -n 1 processing_file.csv); do
    echo "$var_1" "$var_2"
    if (( $(echo "$var_1 >= 200 && $var_1 <= 400 && $var_2 <= 100 && $var_2 >= 0" | bc -l) )); then
        echo -n "m" > "$acm"  # send 'm' without newline
        sleep 1  # delay to prevent rapid multiple sends
    fi
done


#Circular zone - specific distance
#~ acm=$(printf /dev/ttyACM*)
#~ acm=$(printf /dev/ttyUSB*)
#~ xtrigger=100
#~ ytrigger=200
#~ td=100 #threshold distance
#~ stty -F "$acm" -hupcl
#~ while IFS=, read -r a b var_1 var_2 < <(tail -n 1 processing_file.csv); do
    #~ echo "$var_1" "$var_2"
    #~ if (( $(echo "scale=2; sqrt(($var_1 - $xtrigger)^2 + ($var_2 - $ytrigger)^2) < $td" | bc -l) )); then
        #~ echo -n "m" > "$acm"  # send 'm' without newline
        #~ sleep 1  # delay to prevent rapid multiple sends
    #~ fi
#~ done


