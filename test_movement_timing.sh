#!/bin/bash

echo "Testing movement timing and functionality..."
echo "Starting from center position (200 = x:0, y:10)"
echo ""

cd /home/nice/Uni/Master/ASE2026/ASE2026/projects/emulator/build

# Test individual movements with timing
start_time=$(date +%s%N)

# Create a FIFO for sending commands
mkfifo test_fifo

# Start the emulator in background, reading from FIFO
./emulator_runner movement.elf --movement < test_fifo > output.txt 2>&1 &
EMULATOR_PID=$!

# Give it time to start
sleep 2

# Send test sequence: right, right, down, down, left, up
echo "l" > test_fifo  # right from (0,10) -> (1,10)
sleep 0.5
echo "l" > test_fifo  # right from (1,10) -> (2,10)
sleep 0.5
echo "j" > test_fifo  # down from (2,10) -> (2,11)
sleep 0.5
echo "j" > test_fifo  # down from (2,11) -> (2,12)
sleep 0.5
echo "h" > test_fifo  # left from (2,12) -> (1,12)
sleep 0.5
echo "k" > test_fifo  # up from (1,12) -> (1,11)
sleep 0.5
echo "q" > test_fifo  # quit

# Wait for emulator to finish
wait $EMULATOR_PID

end_time=$(date +%s%N)

# Clean up
rm test_fifo

# Calculate duration
duration_ms=$(( (end_time - start_time) / 1000000 ))

# Show results
echo "=== Movement Test Results ==="
echo "Total test duration: $duration_ms ms"
echo ""
echo "Movement sequence:"
grep -E "(Key:|Neural prediction)" output.txt

# Calculate movements per second
movement_count=$(grep -c "Neural prediction" output.txt)
if [ $movement_count -gt 0 ]; then
    movements_per_second=$(echo "scale=2; $movement_count * 1000 / $duration_ms" | bc)
    echo ""
    echo "Performance: $movements_per_second movements/second"
fi

rm output.txt