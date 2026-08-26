![Raspberry Pi RP2040 Embedded System, Retro Game Porting](images/hero.jpg)

The **Raspberry Pi RP2040 Embedded System, Retro Game Porting** board is a compact RP2040-based embedded learning and application platform that combines a color display, handheld controls, motion sensing, infrared communication, audio output, and expansion interfaces for firmware development and retro-style game projects.

* **Raspberry Pi RP2040** with dual Arm Cortex-M0+ cores running at up to 133 MHz
* **264 KB on-chip SRAM** and **2 MB external serial flash** on the documented Game Kit configuration
* **240 × 240 color IPS LCD** using an ST7789 controller over SPI
* Analog joystick, programmable keys, MMA7660 three-axis motion sensor, buzzer, and infrared transmitter/receiver
* MicroPython and C/C++ development support
* USB Type-C connection for power and program download

## Why Raspberry Pi RP2040 Embedded System, Retro Game Porting

A minimal RP2040 development board is a good platform for learning GPIO, timers, interrupts, and basic firmware, but it does not provide a complete interactive embedded system by itself. Building a handheld application around a minimal board normally means selecting and wiring a display, directional controls, buttons, audio hardware, sensors, and power connections before application development can begin. That process is useful when learning PCB design or low-level hardware integration, but it creates many independent failure points when the goal is to study embedded software, user-interface design, or game porting. This board keeps those common peripherals together as a known hardware target so software behavior can be explored without rebuilding the physical system for each exercise.

The board is centered on Raspberry Pi's **RP2040** microcontroller and combines it with a **240 × 240 ST7789 color LCD**, analog joystick, programmable keys, **MMA7660 three-axis motion sensor**, infrared transmit/receive hardware, buzzer, and a dual-row expansion interface. This combination is particularly useful for projects that need both user input and visual output. A developer can move from GPIO and ADC exercises to graphics, menus, motion-controlled applications, USB interfaces, infrared protocols, small instruments, and complete retro-style games while continuing to use the same board.

The target audience includes embedded-systems students, first-time RP2040 developers, makers learning MicroPython, developers porting small games to microcontrollers, and engineers who want a compact RP2040 control-and-display platform for repeatable experiments. The reference project material includes peripheral demonstrations, display drivers, HID-oriented experiments, a snake-style game, and NES-related demonstration material. The board can therefore be approached both as a learning platform and as a practical target for studying how a complete interactive application fits within microcontroller RAM, flash, display, input, and timing constraints. Product material also describes the board as a possible control and display interface for electronics-competition projects when external sensors or analog circuitry are connected.

Compared with a conventional teaching board that provides only LEDs, switches, and headers, this platform supports substantially richer user interaction through its LCD, joystick, motion sensor, infrared hardware, and sound output. Compared with a finished handheld game console, it leaves the embedded implementation visible: developers can change the display driver, input processing, rendering loop, peripheral control, resource layout, and application software. Compared with a Raspberry Pi Linux computer, it provides a much smaller bare-metal or MicroPython-style environment where timing, memory usage, frame rendering, and peripheral access remain explicit parts of the design.

There are also clear limits. This board is not a Linux single-board computer and does not provide the memory, storage, operating-system environment, GPU, or application ecosystem of a Raspberry Pi computer. Wi-Fi and Bluetooth are not documented as onboard features, and the board is not intended for high-current motors, 5 V digital interfaces without level conversion, or applications requiring many completely uncommitted GPIO pins. Developers who need large frame buffers, complex 3D graphics, modern-console emulation, industrial I/O, extensive external memory, or high-speed networking should choose hardware sized for those requirements rather than expecting the RP2040 Game Kit to replace a more powerful system.

## Quick Start

The shortest documented path to a working first result is to use **MicroPython** and **Thonny**. The product material describes the external flash as being loaded with a MicroPython UF2 image, although the exact production firmware version and filename still need to be recorded for this repository. Starting with a simple onboard LED test is preferable to launching a game immediately because it verifies USB communication, firmware execution, interpreter configuration, and the board pin map with the fewest dependencies.

### 1. Connect USB and Power

1. Place the board on a non-conductive surface and leave the expansion connector disconnected during the first test.
2. Connect a **USB Type-C data cable** to the board's USB Type-C port and then to the host computer.
3. The USB connection provides normal board power and is also used for program download.
4. Wait for the operating system to enumerate the RP2040 USB device.
5. If the shipping MicroPython firmware is installed, the board should become available to a suitable MicroPython development environment.
6. Observe the board for normal startup behavior. The software mapping identifies an onboard status LED on GPIO 4, but its initial state depends on the firmware currently installed.

Do not assume that a cable is suitable simply because the board receives power. A charge-only USB cable can power the RP2040 and display while providing no data connection to the computer. If the board appears powered but no development interface can be found, testing a known-good USB data cable should be the first troubleshooting step.



### 2. Install the Toolchain / IDE

For a first MicroPython project, install **Thonny**, which is referenced by the project learning material.

1. Launch Thonny.
2. Open the interpreter configuration.
3. Select the MicroPython interpreter intended for an RP2040 / Raspberry Pi Pico-class device.
4. Select the serial device corresponding to the connected board.
5. Restart the interpreter if required.
6. Confirm that an interactive MicroPython prompt appears in the Thonny shell.

The product documentation also lists **C and C++** as supported programming languages. Those workflows can use the Raspberry Pi RP2040 development ecosystem and Pico SDK, but the exact repository-supported SDK version, compiler release, CMake version, and build commands still need to be recorded. MicroPython is therefore the preferred first-boot path in this README because the board-specific examples and preloaded firmware are documented around that environment.



> [!TIP]
> If Thonny cannot see the board, first replace the USB cable and close any serial terminal that may already have opened the port. Do not install an arbitrary USB driver unless the board documentation specifically identifies one as required.

### 3. Run the First Example

The board-support configuration maps the onboard status LED to **GPIO 4**. A minimal MicroPython blink program is therefore a useful first test:

```python
from machine import Pin
from time import sleep

status_led = Pin(4, Pin.OUT)

while True:
    status_led.toggle()
    sleep(0.5)
```

Run the script from Thonny. The status LED should toggle every 500 ms. If the shell remains responsive but the LED does not change, stop the program and confirm that the current PCB revision uses the same GPIO 4 mapping as the reference `board.py`.

After the LED example works, move to one peripheral at a time. A sensible progression is keys, joystick, buzzer, LCD, MMA7660 motion sensing, and infrared communication before loading a complete game. This makes failures easier to isolate because a game may depend simultaneously on the LCD driver, font or image resources, button handling, timing code, and board-support modules.

To start an application automatically after reset under MicroPython, save the tested startup script using the filename expected by the installed MicroPython environment, normally `main.py`. More complex applications may require additional driver, font, image, sound, or resource files to be copied to the board as well.

### Troubleshooting First Boot

**The board receives power, but no MicroPython serial device appears.** Try a known-good USB Type-C data cable and connect directly to the host rather than through an unpowered hub. Close other programs that may have opened the serial device. If the firmware has been erased, use the board-specific UF2 recovery workflow once that procedure has been verified and committed.

**Thonny reports that the board is busy or cannot enter raw REPL.** Stop the currently running program and restart the MicroPython interpreter from Thonny. A continuous display-update loop, interrupt handler, or game application can make the REPL appear unavailable. If a startup program immediately takes control after every reset, follow the documented recovery procedure to temporarily remove or replace it.

**The MicroPython shell works, but the LCD or controls do not.** Verify that the application uses the Game Kit pin map rather than a generic Raspberry Pi Pico mapping. The documented LCD uses GPIO 2, GPIO 3, GPIO 0, and GPIO 1; the joystick uses GPIO 29 and GPIO 28; and the reference key inputs use GPIO 5 through GPIO 8. Also check that all required display-driver and resource files are present on the device.

## Board Overview

![Board layout](images/layout.png)

The RP2040 Game Kit places the main processor, handheld user interface, sensors, communication peripherals, and expansion interface on one board. The goal is not to hide the RP2040 behind a finished appliance, but to provide a repeatable embedded-system target where developers can study how several peripherals are coordinated by one application. The board photographs and software mapping should be used together with the schematic because some RP2040 pins are already assigned to onboard functions.

### Main IC

The main controller is the **Raspberry Pi RP2040**. It contains two Arm Cortex-M0+ processor cores and is documented to operate at up to 133 MHz. The RP2040 includes 264 KB of on-chip SRAM, programmable I/O blocks, SPI and I2C controllers, PWM hardware, USB support, an internal temperature sensor, and a 12-bit ADC subsystem.

The documented Game Kit configuration also includes **2 MB of external serial flash**. Program code, MicroPython firmware, image resources, fonts, sounds, and application data must share the available flash capacity. Game ports in particular benefit from explicit resource planning because graphical assets can consume storage and runtime memory quickly.

### Connectors

The primary development connector is **USB Type-C**. It supplies power and provides the normal program-download connection, so an additional USB-to-UART programming adapter is not required for the documented MicroPython workflow.

The board also provides a **dual-row 16-pin expansion connector**. Product material identifies SPI, I2C, and two analog inputs on this interface. A related hardware description identifies a 2 × 8 connector using 2.54 mm pitch, but the full current connector map must be verified against the production schematic before designing a daughterboard.


### Programmer and Debugger

Normal firmware loading is performed using the RP2040 USB programming path. No separate onboard programmer IC is identified as necessary for the standard MicroPython workflow. This keeps software development close to the conventional Raspberry Pi Pico model.

Hardware-family information also shows a three-pin debug header. This may be intended for an SWD-style connection, but the exact signals, orientation, and voltage reference have not been confirmed in the provided material. Do not connect an SWD probe until the schematic identifies the pin order.


### Display and User Controls

The primary visual interface is a **240 × 240 color IPS LCD** controlled by an ST7789-compatible controller using SPI. The documented software pin map assigns LCD clock to GPIO 2, serial data to GPIO 3, reset to GPIO 0, and data/command to GPIO 1. The display can be used for menus, status interfaces, game graphics, graphs, sensor values, icons, and instrument-style applications.

An analog joystick provides two-axis user input. Its documented X and Y channels are connected to GPIO 29 and GPIO 28 and are read using the RP2040 ADC. Application software can convert these analog values into directional input, proportional control, menu navigation, or HID movement.

The reference software also defines four digital controls named **B, A, Start, and Select** on GPIO 5, GPIO 6, GPIO 7, and GPIO 8. Product photographs show A/B and Start/Select-style controls around the display. Exact switch labels and mechanical implementation should always be matched to the current production board rather than inferred from an older revision.

### Motion Sensor

The onboard **MMA7660** provides three-axis motion and orientation information. The documented interface uses I2C, with SCL on GPIO 11 and SDA on GPIO 10, and an interrupt line on GPIO 9. It can be used for motion-controlled games, tilt interfaces, simple level indicators, orientation sensing, and experiments with interrupt-driven sensor input.

### Infrared and Audio

The board includes an infrared receiver and a **940 nm infrared transmitter LED**. Reference software maps infrared reception to GPIO 25 and infrared transmission to GPIO 24. These resources can be used to study pulse timing, remote-control protocols, command transmission, and event-driven decoding.

A buzzer is mapped to GPIO 23. It can generate alerts, game effects, simple melodies, and PWM-based audio demonstrations. The learning material also references an optional microphone-amplifier module for audio-oriented acquisition experiments.

### Expansion Headers

The expansion header provides access to selected RP2040 interfaces for sensors, analog circuits, external LEDs, wireless modules, servos, and other experiment hardware. The documentation explicitly identifies SPI, I2C, and two analog-input resources. Because many RP2040 pins are already connected to onboard devices, the available expansion signals must be treated as a defined interface rather than assuming that every RP2040 GPIO is free.

External digital signals should be designed for the board's 3.3 V logic domain unless the schematic explicitly documents level shifting. Bus conflicts are also possible when an external device uses a pin or bus resource already occupied by the LCD, MMA7660, joystick, infrared hardware, buzzer, or buttons.

### Power Circuitry

USB Type-C is the documented normal power source. A regulator identified in related hardware information is the XT3406, but component-level maximum ratings should not be interpreted as the permitted board-level power-input specification. The complete production power path, available external-module current, and expansion-header power behavior still require documentation.


## Hardware Features

![Onboard resources](images/resources.png)

The hardware is organized around interactive embedded-system development rather than a single fixed application. The display, joystick, keys, sensor, infrared circuitry, buzzer, and expansion interface are all accessible through normal RP2040 firmware, making them useful both individually and as parts of a complete program.

### Main IC

* **Raspberry Pi RP2040** microcontroller
* Dual Arm Cortex-M0+ processor cores
* Maximum documented operating frequency of 133 MHz
* 264 KB on-chip SRAM
* 2 MB external serial flash on the documented Game Kit configuration
* Programmable I/O blocks for timing-sensitive custom interfaces
* Internal temperature sensor
* 12-bit ADC subsystem
* RP2040 ADC architecture supports up to four external analog inputs
* ADC sampling rate documented up to 500 kS/s
* MicroPython, C, and C++ development support

The dual-core architecture allows applications to explore concurrency, although software should not assume that every project benefits automatically from splitting work between both cores. Display rendering, input processing, communications, and application logic still need appropriate synchronization when shared state or hardware resources are involved.

### Onboard I/O

* **240 × 240 color IPS LCD** using an ST7789 controller and SPI
* **Two-axis analog joystick**
* **Programmable digital keys** defined in the reference software as B, A, Start, and Select
* **MMA7660 three-axis motion sensor**
* **Infrared receiver**
* **940 nm infrared transmitter LED**
* **Buzzer** for tones, alerts, and game sound effects
* **Status LED** mapped to GPIO 4 in the documented software configuration
* Optional microphone-amplifier hardware referenced by the learning material

These peripherals allow an application to combine analog sampling, digital input, SPI graphics, I2C sensing, PWM/audio output, timed infrared communication, and application-level state management on the same target. That makes the board especially useful for exercises that go beyond isolated peripheral tests.

### Expansion and Programming

* USB Type-C for power and program download
* Dual-row 16-pin expansion interface
* SPI available on the expansion interface
* I2C available on the expansion interface
* Two analog inputs documented on the expansion interface
* MicroPython support
* C and C++ support
* Board-specific UF2 firmware used by project material

> [!NOTE]
> The expansion connector does not imply that every RP2040 GPIO is externally accessible. Check the pin map and onboard pin conflicts before assigning a peripheral.

### Power

* USB Type-C for normal board power
* 3.3 V-class RP2040 signal domain

> [!WARNING]
> The supplied documentation does not state that any RP2040 Game Kit GPIO is 5 V tolerant. Treat external digital and analog signals as 3.3 V-domain signals and use appropriate level shifting or voltage division when interfacing with higher-voltage hardware.

## Available Versions

The supplied product documentation describes one RP2040 Game Kit hardware configuration. A referenced schematic filename includes `V3-20211228`, indicating that hardware revisioning exists, but a complete production revision or SKU matrix is not yet available.

| Version / SKU                                                  | Main IC             | Key differentiating specifications                                                                | Unique features / notes                                                     |
| -------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |

> [!IMPORTANT]
> Select an **RP2040-compatible target** in MicroPython, the Pico SDK, or another development environment. If repository board definitions become revision-specific, select the definition that matches the PCB revision and flash configuration printed on your physical board.

A firmware image intended for a similar RP2040 board can still use different LCD pins, flash settings, button assignments, or sensor addresses. Always identify the actual board revision before distributing a classroom firmware image or compiling a fixed production configuration.

## Board Dimensions

![Dimensions](images/dimensions.png)

Verified board-outline dimensions were not included in the source material used for this README. Do not calculate mechanical data by scaling product photographs because perspective, enclosure overhang, joystick height, and connector protrusion can produce incorrect values. The final dimensions should come from the PCB CAD files or a controlled mechanical drawing.

| Mechanical item           | Verified value                                                                |
| ------------------------- | ----------------------------------------------------------------------------- |
| Expansion-header format   | Dual-row 16-pin                                                               |
| Expansion-header pitch    | 2.54 mm for the documented 2 × 8 footprint                                    |

The mechanical drawing should also define keep-out areas around the joystick, buttons, LCD, USB Type-C connector, on/off control if fitted, and expansion connector. These details matter when designing a 3D-printed enclosure or a custom carrier that sits close to the board.

## Pinout

![Pinout diagram](images/pinout.png)

The onboard mapping below is taken from the documented Game Kit `board.py` configuration. It should be treated as the software/hardware interface for the documented revision and checked against the current schematic when a new production revision is introduced.

| Function             | RP2040 GPIO | Interface / role             |
| -------------------- | ----------: | ---------------------------- |
| LCD reset            |           0 | ST7789 control               |
| LCD data/command     |           1 | ST7789 control               |
| LCD SCK              |           2 | SPI clock                    |
| LCD SDA / MOSI       |           3 | SPI serial data              |
| Status LED           |           4 | Digital output               |
| Key B                |           5 | Digital input                |
| Key A                |           6 | Digital input                |
| Key Start            |           7 | Digital input                |
| Key Select           |           8 | Digital input                |
| MMA7660 interrupt    |           9 | Digital interrupt input      |
| MMA7660 SDA          |          10 | I2C data                     |
| MMA7660 SCL          |          11 | I2C clock                    |
| Buzzer               |          23 | Digital / PWM-capable output |
| Infrared transmitter |          24 | Timed / PWM-capable output   |
| Infrared receiver    |          25 | Digital input                |
| Joystick Y           |          28 | ADC input                    |
| Joystick X           |          29 | ADC input                    |

The expansion connector is documented as exposing SPI, I2C, and two analog inputs, but the complete physical pin order has not been supplied in the source set. The final repository pin map should identify connector position, RP2040 GPIO, default interface, analog capability, voltage domain, power pins, grounds, and any conflicts with onboard resources.

Because the LCD, joystick, keys, accelerometer, buzzer, and infrared circuitry consume a significant number of GPIOs, external expansion designs must not assume that every RP2040 function is available on a convenient pin. A daughterboard should be designed from the board schematic and connector map rather than from the generic RP2040 datasheet alone.

> [!WARNING]
> Use **3.3 V logic** on GPIO connections unless a specific signal is documented otherwise. The current source material does not confirm 5 V tolerance for the Game Kit I/O, and applying an out-of-range signal can damage the RP2040 or another onboard device.


## Applications

![Applications](images/applications.png)

The board can be used as both an embedded-systems teaching target and a compact interactive controller. The examples below focus on applications supported by the documented peripherals rather than hypothetical features.

### Embedded-Systems Coursework

The board supports a progression from simple GPIO programs to complete multi-peripheral applications. A course can begin with the status LED and digital keys, move into joystick ADC sampling and buzzer PWM, then introduce SPI display programming, I2C motion sensing, infrared timing, and external expansion hardware. Using a fixed board reduces wiring differences between students and makes software behavior easier to reproduce across a classroom.

### Retro Game Porting

The LCD, analog joystick, A/B controls, Start/Select inputs, buzzer, and RP2040 processing resources provide the basic structure needed for small handheld game projects. The supplied material includes multiple retro-game demonstrations as well as snake-style and NES-related reference files. Porting a game to this board is useful for studying frame timing, input handling, graphics conversion, asset storage, memory limits, and audio under microcontroller constraints.

A game port should include only code and assets that may legally be redistributed. Emulator demonstrations do not imply that commercial game ROMs are included with this repository.

### Menu-Driven Embedded User Interfaces

The ST7789 LCD and physical controls can form a compact front panel for a custom embedded device. Applications can display operating modes, sensor values, configuration menus, graphs, or error states while the joystick and buttons provide local control. This is useful when prototyping a system that should operate without a permanently attached PC.

### Motion-Controlled Applications

The MMA7660 can provide tilt and movement information for games, digital-level demonstrations, menu navigation, or experimental motion interfaces. The dedicated interrupt line also gives students a practical example of event-driven sensor handling rather than continuously polling every peripheral. More advanced projects can combine joystick and motion input to compare different interaction methods.

### Infrared Protocol Experiments

The infrared transmitter and receiver can be used to study common remote-control communication concepts. Developers can measure pulse lengths, decode incoming commands, generate carrier-modulated signals, and display captured data on the LCD. Game or interactive projects can also use infrared as a simple device-to-device control channel when supported by application software.

### USB HID Experiments

The RP2040 USB interface and onboard controls can be combined in HID-oriented projects. Reference material includes mouse/controller-style experiments using board input devices. This makes the board useful for studying USB input devices, dead zones, analog-to-digital input mapping, button debouncing, and host-visible control behavior.

### Graphical Instruments and Data Displays

External sensors or analog front ends can send data to the board through the expansion connector while the LCD acts as the local display. The learning material references microphone and waveform-oriented experiments in addition to normal sensor applications. This allows the board to be used as a small display/control front end for electronics experiments, although it should not be described as a calibrated measurement instrument unless the attached hardware is characterized accordingly.

### Electronics-Competition Prototypes

Official product material identifies the Game Kit as a possible control and display platform for electronics-competition projects. External sensors, analog circuits, or control modules can connect through the expansion interface while the built-in LCD, joystick, keys, and buzzer provide the user interface. This can save time when the competition task is focused on algorithms or external circuitry rather than designing another control panel from scratch.

## Factory Demo

![Factory demo](images/demo.gif)

The board documentation describes the external flash as being loaded with a MicroPython UF2 image, but the exact current production demo has not been established in the supplied material. The reference project contains display examples, input demonstrations, sound code, MMA7660 examples, infrared functions, HID material, snake-style software, and NES-related demonstration resources. These resources show the range of board functions that can be tested, but they should not be presented as one guaranteed shipping demo unless the fulfillment image is fixed and documented.

A useful production self-test should verify the LCD, joystick axes, A/B and Start/Select controls, MMA7660 communication, buzzer, status LED, infrared hardware, external flash, and any accessible expansion resources. The display can present pass/fail feedback while the user moves controls or triggers sensors. This approach makes the demo useful not only as an application sample but also as a first-line diagnostic when a board is received.

The demo should also display or expose a firmware version and hardware-revision identifier. Without that information, two boards with different production firmware can behave differently while appearing physically identical. A documented restoration workflow is equally important so developers can experiment freely and then return the board to a known reference configuration.



## Repository Structure

```text
.
├── docs/       Documentation
├── examples/   Self-contained example projects
├── project/    Project files and templates
├── hardware/   Schematic and mechanical references
├── software/   PC-side utilities and drivers
└── images/     Artwork for README and docs
```

`docs/` is the primary documentation directory. It should contain the quick-start guide, complete pin mapping, programming notes, firmware-recovery procedure, game-porting guidance, classroom material, and revision-specific hardware information.

`examples/` contains focused projects that demonstrate one peripheral or concept at a time. Each example should include its dependencies, required hardware, tested firmware/toolchain version, expected output, and troubleshooting information.

`project/` contains reusable application templates and complete development projects. Pico SDK starter projects, CMake files, MicroPython project layouts, and more complex game-porting projects should live here rather than being mixed with minimal examples.

`hardware/` stores the schematic, board-revision references, connector details, mechanical drawings, and optional-module schematics. Electrical limits and pin assignments should always be traceable to a specific hardware revision.

`software/` contains host-side utilities, firmware images, file-transfer helpers, recovery tools, and operating-system setup notes. Software distributed here should state its source, license, and tested version.

`images/` contains stable product photographs, board diagrams, pinout graphics, application examples, package images, and demo media used by this README and related documents.

## Documentation

The following relative paths define the intended documentation structure:

* [Quick Start Guide](docs/quick-start.md)
* [Complete Pin Map](docs/pin-map.md)
* [Firmware Recovery Guide](docs/firmware-recovery.md)
* [Hardware Documentation](docs/)
* [Game Kit Schematic](hardware/game2040-V3-20211228.pdf)
* [Microphone Amplifier Schematic](hardware/mic_amp.pdf)
* [Mechanical Drawing](hardware/mechanical-drawing.pdf)
* [Software Notes](software/README.md)

> [!NOTE]
> Some paths above reflect the intended repository organization and still require confirmation or file migration. Do not publish a release with broken documentation links; either commit the referenced file or update the link to the actual filename.

The hardware documentation should state which PCB revision each schematic and mechanical drawing describes. This is especially important for the buttons, expansion connector, flash device, debug header, and power circuit, which may change between revisions without changing the general product name.

Firmware and software documentation should also state the exact MicroPython or Pico SDK version used. Game ports and graphics applications can depend on memory behavior, drivers, and display initialization details that change when the software stack changes.

## Examples

The reference project material contains examples for most of the board's major peripherals and several complete applications. The list below is organized as a recommended repository structure; items should remain checked only when the corresponding self-contained example has actually been committed under `examples/`.

* [x] `led-blink` — toggles the status LED on GPIO 4 and verifies basic toolchain/board operation
* [x] `buttons` — reads the documented B, A, Start, and Select inputs
* [x] `joystick` — samples the analog joystick on GPIO 29 and GPIO 28
* [x] `buzzer` — verifies buzzer operation and basic PWM output
* [x] `buzzer-music` — demonstrates tone and melody generation
* [x] `st7789-display` — initializes the 240 × 240 display and draws text or graphics
* [x] `mma7660` — reads the onboard three-axis motion sensor through I2C
* [x] `infrared` — demonstrates infrared receive and transmit functions
* [x] `microphone` — samples the optional microphone-amplifier input
* [x] `servo` — demonstrates control of an external servo through the expansion interface
* [x] `ws2812` — controls addressable LEDs and can be extended into a PIO exercise
* [x] `hid-controller` — uses onboard controls for USB HID-oriented experiments
* [x] `snake-game` — combines graphics, controls, timing, and game state
* [x] `nes-demo` — reference material for a retro-game/emulation demonstration
* [ ] `expansion-header-test` — validates each documented external interface and connector position
* [ ] `factory-self-test` — verifies LCD, controls, motion sensor, buzzer, infrared, flash, and expansion resources

Each example should be runnable from a clean clone and should not silently depend on files stored elsewhere on the developer's computer. MicroPython examples that require display drivers, fonts, bitmaps, or audio assets should document the final filesystem layout on the RP2040 flash.

Complete game ports should include a description of their origin and licensing. Source code that is open source does not automatically make game artwork, music, fonts, or ROM data redistributable. Keep third-party assets clearly separated and document what the user must provide independently.

> [!TIP]
> When porting a game, first verify the display and input examples independently. A game that boots to a blank screen can otherwise involve too many possible causes at once: display initialization, file paths, memory use, image format, control mapping, or application logic.

## Software Compatibility

The provided project material explicitly supports **MicroPython**, **C**, and **C++** development. MicroPython with Thonny is the most directly documented learning workflow, while compiled applications can use the RP2040 C/C++ ecosystem. Other environments should be described separately unless they have been validated on this exact board configuration.

| Environment                 | Language                       | Supported status                                         | Host platforms            | Notes                                                              |
| --------------------------- | ------------------------------ | -------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------ |
| Arduino RP2040 ecosystem    | C / C++                        | Community use exists; not primary documented environment | Windows, macOS, Linux     | Treat as community-supported until a board definition is validated |

### Windows

Thonny can be used for the MicroPython workflow, while Pico SDK development requires the normal compiler and CMake environment. The supplied product material does not identify a proprietary USB driver as required. If the board does not appear, verify the data cable and Device Manager before installing third-party drivers.

### macOS

MicroPython development should use the serial device exposed after the board is connected. The exact minimum tested macOS version and Apple Silicon support have not been recorded. Pico SDK projects should document the compiler and CMake versions used by repository releases.

### Linux

Serial access may depend on the user's group membership or local device permissions. A project-specific udev rule should be added only after the board identifiers and required access have been verified. Distribution, kernel, compiler, Python, and CMake versions should be recorded for tested release environments.

> [!NOTE]
> Retro-game demonstrations may include additional software or third-party components with licenses that differ from the board-support code. Review emulator cores, libraries, fonts, graphics, sounds, and example assets individually before redistributing them.

## Package Contents

![Package contents](images/package.jpg)

The current source material confirms the main RP2040 Game Kit hardware but does not provide a complete controlled retail packing list. Package contents should be checked against the exact SKU before this section is used for fulfillment.

* **1 × Raspberry Pi RP2040 Embedded System / RP2040 Game Kit**

Do not assume that external sensors, wireless modules, servos, addressable LEDs, or analog experiment circuits shown in learning material are included with the base Game Kit. Those should be listed explicitly only when they are part of the SKU being shipped.

## FAQ

### Hardware and Power

### What is the main processor?

The board uses the **Raspberry Pi RP2040**, a dual-core Arm Cortex-M0+ microcontroller documented to operate at up to 133 MHz. It contains 264 KB of on-chip SRAM and provides USB, ADC, PWM, serial interfaces, and programmable I/O resources. The documented Game Kit configuration adds 2 MB of external serial flash for firmware and application resources.

### What display does the board use?

The board uses a **240 × 240 color IPS LCD** with an ST7789 controller connected through SPI. The reference configuration assigns GPIO 2 to the display clock, GPIO 3 to serial data, GPIO 0 to reset, and GPIO 1 to data/command. Display drivers should also document orientation, controller offsets, color ordering, and any frame-buffer strategy used by a project.

### What power source should I use?

Use the board's USB Type-C connection for normal development and first boot. USB power is the board-level supply method explicitly confirmed in the product material. External powering through the expansion connector should not be attempted until the schematic documents the permitted voltage, direction, and current limits.

### Are the GPIO pins 5 V tolerant?

The supplied board documentation does not state that the Game Kit GPIO is 5 V tolerant. Treat external inputs and outputs as **3.3 V-domain signals** and use a level shifter or suitable voltage divider where required. This applies especially to 5 V sensor modules, serial adapters, addressable LEDs, and other boards that may actively drive a high logic level.

### How much memory is available?

The RP2040 provides **264 KB SRAM**, and the documented Game Kit configuration uses **2 MB external serial flash**. Firmware, Python modules, fonts, graphics, sounds, and game assets all consume the available flash. Large graphical applications should also pay close attention to RAM because a full 240 × 240 framebuffer can occupy a significant fraction of the microcontroller's memory depending on pixel format.

### How are the joystick and game controls connected?

The documented joystick axes use GPIO 29 and GPIO 28 as analog inputs. The reference board configuration defines B, A, Start, and Select on GPIO 5, 6, 7, and 8. If a later PCB revision changes the physical controls, update both the pin-map documentation and all examples together.

### Which motion sensor is onboard?

The board uses an **MMA7660 three-axis motion sensor** over I2C. The documented connections are GPIO 11 for SCL, GPIO 10 for SDA, and GPIO 9 for the interrupt signal. It can be used for tilt input, orientation experiments, movement detection, and motion-controlled games.

### What infrared hardware is available?

The board includes an infrared receiver and a **940 nm infrared transmitter LED**. Reference software maps receive to GPIO 25 and transmit to GPIO 24. The actual remote-control protocol is implemented in software, so transmitting or decoding a specific protocol requires suitable timing logic or a matching library.

### Expansion and Interfaces

### What interfaces are available on the expansion connector?

Product documentation identifies a dual-row 16-pin expansion connector with **SPI, I2C, and two analog inputs**. The complete physical order of power, ground, and signal pins still needs to be committed to the repository. Check `docs/pin-map.md` and the schematic before making a daughterboard or cable.

### Can I connect external sensors and analog circuits?

Yes, provided the sensor or circuit matches the documented voltage and pin requirements. The expansion interface is specifically intended for additional hardware, and official product material describes connecting sensors and analog-circuit peripherals. Check for onboard pin conflicts and avoid applying signals outside the 3.3 V RP2040 logic domain.

### Does the board have Wi-Fi or Bluetooth?

Wireless networking is not listed as an onboard feature of the base Game Kit. A related project demonstrates expansion using an external ESP32-S2 module, showing that wireless applications can be added externally. The power budget, interface pins, and software protocol must be verified before attaching a wireless module.

### Programming

### Which programming languages can I use?

The project documentation explicitly identifies **MicroPython, C, and C++**. MicroPython with Thonny is the most directly documented beginner workflow and is suitable for interactive peripheral experiments and many small games. Compiled C/C++ is useful when tighter timing, lower overhead, or more control over memory and peripherals is required.

### What should I program first?

Start with the GPIO 4 status-LED blink example. That test verifies power, USB data communication, MicroPython execution, and the basic board mapping without depending on display libraries or resource files. After it works, test controls and the LCD separately before attempting a full game.

### How do I recover the firmware if an application no longer boots?

The project material contains multiple UF2 firmware images, but the exact production recovery image and board-specific boot procedure still need to be identified. A complete recovery guide should document how to enter UF2 mode, what the host should display, which firmware file to use, and how to verify the restored board. Do not assume that a generic Pico button sequence is available on this PCB unless the required control is actually exposed.

### Can I debug C/C++ using SWD?

Hardware-family information indicates a three-pin debug header, but its exact signals and orientation are not yet confirmed in this documentation. Verify the schematic before attaching a probe. Once confirmed, the repository should document at least one tested SWD probe and an OpenOCD or equivalent debug configuration.

### Games and Software

### Can this board run retro games?

Yes, the provided project material includes several retro-style game demonstrations and porting examples, including snake-style software and NES-related resources. Actual compatibility depends on the program's CPU, RAM, flash, graphics, input, and timing requirements. The board should not be described as supporting every retro platform or every game.

### Are game ROMs included?

This README does not assume that copyrighted commercial ROMs are included. Emulator code and game content have separate legal and licensing considerations, and users should supply only content they are legally permitted to use. Repository releases should clearly separate redistributable source code from third-party or user-supplied assets.

### Why might a game need more files than its main Python script?

Graphical applications commonly depend on display drivers, board-support code, fonts, bitmaps, maps, sounds, or configuration files. Those files must be stored in the correct locations on the board's flash. Every game example should document its complete target-side filesystem so a user can reproduce the setup from a clean board.

## License

The project materials used for this README do not currently establish a finalized top-level repository license. Until explicit license files and copyright notices are committed, original project material should be treated as **all rights reserved** unless an individual file clearly states another license.

If this repository is formally released as open source, suitable license families may include:

* **MIT**, BSD-3-Clause, or Apache-2.0 for original software
* **CERN-OHL** variants for original hardware design sources
* **CC BY 4.0** or **CC BY-SA 4.0** for original documentation and artwork

These are possible choices, not the current license. Emulator projects, MicroPython libraries, display drivers, fonts, sample graphics, game engines, audio files, course material, and other third-party components retain their own license terms.


## Contributing

Bug reports should include the **hardware revision, PCB markings, firmware version or UF2 filename, operating system, development environment, toolchain version, and complete reproduction steps**. If the issue concerns an external module, include the module name, supply voltage, wiring, and the exact expansion pins used. For display or game issues, screenshots or photographs are useful, but also include the terminal output and application files needed to reproduce the problem.

Documentation fixes are welcome, especially improvements to pin mappings, setup instructions, recovery procedures, diagrams, and revision notes. Any change to an electrical limit or connector pin assignment should be supported by the schematic or another controlled hardware source rather than inferred from an example program. Translations should preserve commands, filenames, warnings, and numerical values exactly.

New examples should be self-contained, cleanly runnable from a fresh checkout, and documented for the exact firmware or toolchain version used during testing. Each example should have a README that explains its purpose, required files, pin usage, setup steps, expected behavior, and common failure modes. MicroPython applications should show the final on-device file structure, while Pico SDK projects should include complete and reproducible build files.

New game ports require additional care. Include the origin and license of the code, explain how controls are mapped, document graphics and audio formats, state the expected memory/storage requirements, and avoid committing copyrighted commercial ROMs or assets unless redistribution is explicitly permitted. If users must supply their own game data, explain where it belongs without bundling unlicensed material.

Hardware changes should be discussed in an issue before a major schematic or PCB revision is submitted. Changes to the LCD, flash memory, joystick, expansion connector, USB circuitry, regulator, motion sensor, button mapping, or infrared path can invalidate several examples simultaneously and should therefore include a compatibility and validation plan.

Keep pull requests focused on one logical change whenever possible. A game port should not also reformat every documentation file, and a pin-map correction should not be combined with an unrelated firmware refactor. Focused PRs are easier to review, test on physical hardware, and backport across revisions.