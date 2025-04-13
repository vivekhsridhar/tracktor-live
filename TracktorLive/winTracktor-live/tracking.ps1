# PowerShell script to translate Bash code for Windows

# Define the COM port
$comPort = "COM5"  # Replace with the correct COM port

# Open the serial port with parameters
$serialPort = new-Object System.IO.Ports.SerialPort $comPort,9600,None,8,one
$serialPort.Open()

#Uncomment for square zone
function SendIfInSquareZone {
    param ($var1, $var2)
    
    #Limit number of decimals (2 places)
    $var1 = "{0:F2}" -f $var1
    $var2 = "{0:F2}" -f $var2
    
    #output values for debugging
    Write-Output "$var1 $var2"
    if (($var1 -ge 100 -and $var1 -le 400) -and ($var2 -le 400 -and $var2 -ge 0)) {
        $serialPort.Write("m")  # Send 'm' without newline
        Start-Sleep -Seconds 1  # delay to prevent rapid multiple sends
    }
}

############################
#Uncomment for circular zone
#function SendIfInCircularZone {
#    param ($var1, $var2, $xtrigger, $ytrigger, $threshold)
    
#    $distance = [math]::Sqrt([math]::Pow($var1 - $xtrigger, 2) + [math]::Pow($var2 - $ytrigger, 2))
    #Limit number of decimals (2 places)
#    $distance = "{0:F2}" -f $distance
#    Write-Output "$distance"
#    if ($distance -lt $threshold) {
#        $serialPort.Write("m")  # Send 'm' without newline
#        Start-Sleep -Seconds 1  # delay to prevent rapid multiple sends
#    }
#}

# Position and Threshold distance for circular zone

#$xtrigger = 100
#$ytrigger = 50
#$thresholdDistance = 300
###########################

# Read the last line from the CSV file
$csvFile = "processing_file.csv"
while ($true) {
    $lastLine = Get-Content $csvFile | Select-Object -Last 1
    $columns = $lastLine -split ","
    
    $var1 = [double]$columns[1]
    $var2 = [double]$columns[2]
    
#uncomment for square zone
    # Check if in square zone
    SendIfInSquareZone -var1 $var1 -var2 $var2
    
#uncomment for circular zone
    # Check if in circular zone
    #SendIfInCircularZone -var1 $var1 -var2 $var2 -xtrigger $xtrigger -ytrigger $ytrigger -threshold $thresholdDistance
}
$serialPort.Close()

exit