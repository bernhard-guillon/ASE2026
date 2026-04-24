#!/bin/bash

cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/build

# Create a FIFO for sending commands
mkfifo test_fifo

# Start the emulator in background, reading from FIFO
./emulator_runner movement.elf --movement < test_fifo > output.txt 2>&1 &
EMULATOR_PID=$!

# Give it time to start
sleep 2

# Send commands
(echo "h"; sleep 2; echo "j"; sleep 2; echo "k"; sleep 2; echo "l"; sleep 2; echo "q") > test_fifo

# Wait for emulator to finish
wait $EMULATOR_PID

# Clean up
rm test_fifo

# Show results
echo "=== Movement Test Results ==="
grep -E "(Key:|Neural prediction)" output.txt

rm output.txt