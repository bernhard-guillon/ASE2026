# ASE 2026 - Neural driven computing

Neural driven computing, Bernhard Guillon

## Introduction

Traditional computer architectures evolved from simple batch machines to something more sophisticated with the need of something like an operating system. Most computer hardware was single core at the beginning. But the idea to share resureces and give different operations seperated access led to more and more sophisticated operating systems. But basically they offer an abstraction to the hardware and take care about memory, process management and multiprocessing.

As the current LLM and AI boom in general tend to use a hevy environment from starting a whole operationg system to then start a browser which implements a lot a operationg system would also do to then ask the ai to build programs which eventually can run at the browser or directly at the operationg system. As most modern software also wants to include some sort of AI. We wonder if we cannot create something way more lightweight to just load the perceptron based AI to a system.

## Vision

Create a minimal ISA which might be risc-v based and enhance it with some AI instructions like, matmul, activation, tensor ops. For that ISA create an emulator.
The I/O devices should start simple first. A character device with alphanum as input and a simple Framebuffer as output. With that we already have most common I/O devices already as most of them are character based or memory/register based.
Current model therefore is Keyboard input -> natural model -> Framebuffer pixel output.

Therefore we first train a model with something like pytorch wich on a character input will print that input into the framebuffer. We then try to load that model into our emulator. For that we need to define how the bootloader is able to load the model into memory and jump to "something" which is task of the research to figgure out to then start the model.

For that we might need to write an assembler for our architecture. Which we then try to feed into LLM to create us the bootloader. We also need to write a "transpiler" to convert the pythorch output or implement our own neuron trainer for simple tasks.

## How we plan to use AI

We want to use it to create training data for all of our networks we want to run. We also plan to use it to write the emulator. and research on the instructions. As we run everything in an emulator we want to use it to write something to automatically verify results. Something like black box testing. Try to use this as some sort of input for the AI agent to identify and fix issues.

## Stretch goals

The already planned goals might alredy be qute amitious but if we are faster we define the following strech goals:


* Add additional I/O to interact with a second instance of the emulator and define a mechanism to talk to each other.

* Let the LLM write a fake datasheet for a simple device e.g. a sensor which we then pass into a second instance of the LLM to try to create training material for a model we can run on our emulator


