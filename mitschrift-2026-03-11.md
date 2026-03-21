
# TODO:

write a one page pdf to pitch the Idea. Basic idea was accepted

First of all define a Set of RISC-V with addintion to instructions for AI SIMD or GPU

create a emulator for it.

Define inputs and outputs:

Further define the problem and what we want to archive.


Simple first

like having a super simple thing with some inputs and some pixels as output. Input should be later a keyboard

-
-
-
-

define what we need to add to the emulator to train and load a model. For example pressing a getting A on the screen!


Most computer hardware is accessable to a memory location and has registers to talk to. We can map them to input/outputs but we need to research bus width and stuff like that

But we allready have two basic devices defined. A chardev, in our case a keyboard and a memory based framebuffer our output. With these two basic concepts we can drive a lot of devices.

Let AI write a typical datasheet definition about our keyboard and how it is connected to our pc e.g. a shift register or at the beginning a memory range betwee 0 and 255. Let the ai break down that into usefull training data.

And train a model which we can then transpile to our own model. Or also write the AI on our own later. The model should be then able to produce characters on the screen

so if A would be 0x01 it would draw an 

[ ][x][x][ ]
[x][ ][ ][x]
[x][x][x][x]
[x][ ][ ][x]

To our framebuffer aka memory.


Define typical Operating system tasks Perceptron based machine might not need. Like scheduling, seperation of concerns.. 

Define what a simple os is.

And how much wast it is to until e.g. Windows or Linux has started the browser with which you then interact.


Advanced topics
Define how to connect to the "internet" and talk to other AIs or to a world which is not perceptron based!





