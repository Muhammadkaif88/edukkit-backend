import os
import sys
import json

# Ensure UTF-8 output encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, SessionLocal
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.product import Product
from app.models.order import Order
from app.models.payment import Payment, PaymentEvent
from app.models.entitlement import CourseEntitlement
from app.models.user import User

# APPROVED 13 COURSES CATALOG
COURSES_DATA = json.loads('[{"id_str": "feat_electronics_01", "title": "Basic Electronics for Beginners", "category": "Electronics", "description": "Learn electronic components, circuits and practical basics.", "short_description": "Learn electronic components, circuits and practical basics.", "instructor": "Edukkit Team", "price": 599.0, "original_price": 898.5, "level": "Beginner", "thumbnail": "", "is_free": false, "is_published": true, "bunny_collection_id": null}, {"id_str": "feat_robotics_01", "title": "Junior Robotics Engineer", "category": "Robotics", "description": "Learn sensors, motors, controllers and build real robot projects.", "short_description": "Learn sensors, motors, controllers and build real robot projects.", "instructor": "Edukkit Team", "price": 1499.0, "original_price": 2499.0, "level": "Beginner", "thumbnail": "", "is_free": false, "is_published": true, "bunny_collection_id": "730163"}, {"id_str": "feat_iot_01", "title": "IoT & Home Automation", "category": "IoT & Smart Technology", "description": "Build smart home projects and connect devices with IoT.", "short_description": "Build smart home projects and connect devices with IoT.", "instructor": "Edukkit Team", "price": 899.0, "original_price": 1348.5, "level": "Beginner", "thumbnail": "", "is_free": false, "is_published": true, "bunny_collection_id": null}, {"id_str": "pop_electronics_01", "title": "Electronics Fundamentals", "category": "Electronics", "description": "Understand electronic components, circuits & measurements.", "short_description": "Understand electronic components, circuits & measurements.", "instructor": "Edukkit Circuits Team", "price": 799.0, "original_price": 1198.5, "level": "Beginner", "thumbnail": "assets/images/courses/electronics_board_3d.png", "is_free": false, "is_published": true, "bunny_collection_id": null}, {"id_str": "pop_iot_01", "title": "IoT for Beginners", "category": "IoT & Smart Technology", "description": "Build smart IoT projects and connect your ideas to the real world.", "short_description": "Build smart IoT projects and connect your ideas to the real world.", "instructor": "IoT Specialist Lab", "price": 899.0, "original_price": 1348.5, "level": "Beginner", "thumbnail": "assets/images/courses/iot_house_3d.png", "is_free": false, "is_published": true, "bunny_collection_id": null}, {"id_str": "pop_ai_01", "title": "AI Tools & Prompt Engineering", "category": "AI", "description": "Master AI tools and learn powerful prompt engineering.", "short_description": "Master AI tools and learn powerful prompt engineering.", "instructor": "AI Innovation Hub", "price": 0.0, "original_price": 0.0, "level": "All Levels", "thumbnail": "assets/images/courses/advanced_robotics.png", "is_free": true, "is_published": true, "bunny_collection_id": null}, {"id_str": "new_robotics_01", "title": "Senior Robotics Engineer", "category": "Robotics", "description": "Advance your robotics skills and work on complex real-world robot engineering projects.", "short_description": "Advance your robotics skills and work on complex real-world robot engineering projects.", "instructor": "Advanced Robotics Lab", "price": 1499.0, "original_price": 2248.5, "level": "Intermediate", "thumbnail": "assets/images/courses/senior_robotics_banner.png", "is_free": false, "is_published": true, "bunny_collection_id": "730163"}, {"id_str": "new_electronics_01", "title": "PCB Design & Manufacturing", "category": "Electronics", "description": "Learn PCB designing, fabrication and manufacturing.", "short_description": "Learn PCB designing, fabrication and manufacturing.", "instructor": "Hardware Design Studio", "price": 1199.0, "original_price": 1798.5, "level": "Intermediate", "thumbnail": "assets/images/courses/electronics_board_3d.png", "is_free": false, "is_published": true, "bunny_collection_id": null}, {"id_str": "new_3d_01", "title": "3D Printing for Beginners", "category": "3D Printing", "description": "Learn 3D printing from basics and create amazing prints.", "short_description": "Learn 3D printing from basics and create amazing prints.", "instructor": "3D Studio Edukkit", "price": 699.0, "original_price": 1048.5, "level": "Beginner", "thumbnail": "assets/images/courses/junior_automation.png", "is_free": false, "is_published": true, "bunny_collection_id": null}, {"id_str": "cat_rob_03", "title": "Robotics Project Masterclass", "category": "Robotics", "description": "Build impressive robotics projects from scratch and become a confident robotics creator.", "short_description": "Build impressive robotics projects from scratch and become a confident robotics creator.", "instructor": "Edukkit Masterclass Lab", "price": 1999.0, "original_price": 2998.5, "level": "Advanced", "thumbnail": "assets/images/courses/robotics_masterclass_banner.png", "is_free": false, "is_published": true, "bunny_collection_id": "730163"}, {"id_str": "cat_ai_02", "title": "AI + Robotics", "category": "AI", "description": "Integrate computer vision and neural networks with autonomous robotics.", "short_description": "Integrate computer vision and neural networks with autonomous robotics.", "instructor": "RoboAI Studio", "price": 1699.0, "original_price": 2548.5, "level": "Intermediate", "thumbnail": "assets/images/courses/senior_robotics_banner.png", "is_free": false, "is_published": true, "bunny_collection_id": "730163"}, {"id_str": "cat_3d_02", "title": "3D Modeling with Fusion 360", "category": "3D Printing", "description": "Design complex 3D parts & parametric CAD models ready for 3D printing.", "short_description": "Design complex 3D parts & parametric CAD models ready for 3D printing.", "instructor": "Design Studio", "price": 1299.0, "original_price": 1948.5, "level": "Intermediate", "thumbnail": "assets/images/courses/iot_house_3d.png", "is_free": false, "is_published": true, "bunny_collection_id": null}, {"id_str": "cat_iot_02", "title": "Home Automation", "category": "IoT & Smart Technology", "description": "Build Wi-Fi smart switches, environmental sensors & mobile app-controlled devices.", "short_description": "Build Wi-Fi smart switches, environmental sensors & mobile app-controlled devices.", "instructor": "Smart Home Lab", "price": 1399.0, "original_price": 2098.5, "level": "Intermediate", "thumbnail": "assets/images/courses/iot_home_automation.png", "is_free": false, "is_published": true, "bunny_collection_id": null}]')

# APPROVED 45 STORE PRODUCTS CATALOG
PRODUCTS_DATA = json.loads('[{"id_str": "prod_c1", "name": "Junior Robotics Engineer", "slug": "junior-robotics-engineer", "description": "Interactive STEM curriculum teaching robot building, block-to-C++ coding, sensor integration, and motor kinematics with live mentor doubt clearing.", "short_description": "Hands-on Robotics Course for Young Innovators (Ages 8-14)", "price": 1499.0, "original_price": 2499.0, "category": "Courses", "type": "electronics", "stock": 99, "images": ["assets/images/courses/junior_automation.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_c2", "name": "Senior Robotics & ROS", "slug": "senior-robotics-ros", "description": "Comprehensive college and high-school level embedded robotics course covering kinematics, PID motor control, Bluetooth/Wi-Fi remote operation and OpenCV vision.", "short_description": "Advanced Embedded Robotics & Microcontroller Programming", "price": 2199.0, "original_price": 3499.0, "category": "Courses", "type": "electronics", "stock": 80, "images": ["assets/images/courses/advanced_robotics.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_c3", "name": "Electronics Fundamentals", "slug": "electronics-fundamentals", "description": "Master circuit theory, Ohm\\\\", "short_description": "From Atoms to Amplifiers: Complete Electronics Core", "price": 999.0, "original_price": 1999.0, "category": "Courses", "type": "electronics", "stock": 120, "images": ["assets/images/courses/electronics_fundamentals.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_1", "name": "Smart Obstacle Avoiding Car Kit", "slug": "smart-obstacle-avoiding-car-kit", "description": "Build an autonomous 4WD obstacle-avoiding smart car from scratch. Includes dual-layer acrylic chassis, ultrasonic servo turret, L298N motor driver, battery holder and guided schematics.", "short_description": "4WD Autonomous Smart Obstacle Avoiding Robot Kit", "price": 1299.0, "original_price": 1699.0, "category": "DIY Kits", "type": "diy_kit", "stock": 28, "images": ["assets/images/products/smart_robot_car_kit.png"], "is_active": true, "linked_course_id": 1}, {"id_str": "prod_diy_2", "name": "Robotics DIY Rover Kit \\ud83d\\ude80", "slug": "robotics-diy-rover-kit", "description": "All-inclusive rover engineering kit with Bluetooth remote control and ultrasonic collision protection. Build, code and control with your smartphone app.", "short_description": "Bluetooth & Sensor Dual-Mode Robotic Rover Kit", "price": 1499.0, "original_price": 1999.0, "category": "DIY Kits", "type": "diy_kit", "stock": 22, "images": ["assets/images/products/smart_robot_car_kit.png"], "is_active": true, "linked_course_id": 1}, {"id_str": "prod_diy_3", "name": "Automatic Night Lamp Kit", "slug": "automatic-night-lamp-kit", "description": "Learn the fundamentals of analog sensors, transistors, and automatic switching! Automatically illuminates ultra-bright LEDs when the room gets dark using an LDR sensor.", "short_description": "Light-Dependent Resistor Automatic Night Lamp DIY Kit", "price": 499.0, "original_price": 699.0, "category": "DIY Kits", "type": "diy_kit", "stock": 45, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_4", "name": "Bluetooth Speaker DIY Kit", "slug": "bluetooth-speaker-diy-kit", "description": "Assemble your very own portable Bluetooth stereo speaker! Includes 2x 3W full-range stereo speakers, PAM8403 digital amplifier, Bluetooth audio receiver board, and laser-cut wooden enclosure.", "short_description": "Custom Wooden Enclosure 2x3W Bluetooth Stereo Speaker Kit", "price": 899.0, "original_price": 1299.0, "category": "DIY Kits", "type": "diy_kit", "stock": 19, "images": ["assets/images/products/bluetooth_speaker_kit.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_5", "name": "Smart Dustbin DIY Kit", "slug": "smart-dustbin-diy-kit", "description": "Touchless automatic opening dustbin. Uses ultrasonic proximity detection and servo lid mechanism to keep hands 100% clean and hygienic.", "short_description": "Contactless Automatic Smart Dustbin Project Kit", "price": 999.0, "original_price": 1399.0, "category": "DIY Kits", "type": "diy_kit", "stock": 35, "images": ["assets/images/products/smart_dustbin_kit.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_6", "name": "Line Follower Robot Kit", "slug": "line-follower-robot-kit", "description": "Precision path-tracking robot car using dual infrared reflective optical sensors to follow black or white tracks at high speed.", "short_description": "High-Precision Dual IR Optical Line Following Robot", "price": 1199.0, "original_price": 1599.0, "category": "DIY Kits", "type": "diy_kit", "stock": 24, "images": ["assets/images/products/smart_robot_car_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_7", "name": "IoT Smart Home DIY Kit", "slug": "iot-smart-home-diy-kit", "description": "Build a miniature connected smart home with Wi-Fi control! Switch lights, monitor room temperature, detect gas leaks, and view real-time metrics on an OLED screen and mobile dashboard.", "short_description": "ESP32 Wi-Fi Smart Home Automation Learning Kit", "price": 1499.0, "original_price": 2199.0, "category": "DIY Kits", "type": "diy_kit", "stock": 20, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_8", "name": "Arduino Starter DIY Kit", "slug": "arduino-starter-diy-kit", "description": "The ultimate beginner electronics and coding laboratory! Includes Arduino UNO R3, 830-point breadboard, 20+ sensors and actuators, LEDs, buzzers, LCD display, and 30 step-by-step experiment cards.", "short_description": "Complete 30-Experiment Arduino Hardware Learning Kit", "price": 1099.0, "original_price": 1499.0, "category": "DIY Kits", "type": "diy_kit", "stock": 50, "images": ["assets/images/products/electronics_starter_kit.png", "assets/images/products/arduino_uno_r3.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_9", "name": "Mini Weather Station Kit", "slug": "mini-weather-station-kit", "description": "Log and display real-time weather metrics! Measures ambient temperature, relative humidity, barometric atmospheric pressure, and light intensity with live OLED graphic graphs.", "short_description": "Digital Desktop Weather Station with OLED Display", "price": 899.0, "original_price": 1299.0, "category": "DIY Kits", "type": "diy_kit", "stock": 30, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_10", "name": "Smart Water Level Indicator Kit", "slug": "smart-water-level-indicator-kit", "description": "Automatic water reservoir and overhead tank level monitor with 4-level LED indicator and buzzer alert when tank is full or low.", "short_description": "Multi-Level Overhead Water Tank Alarm DIY Kit", "price": 699.0, "original_price": 999.0, "category": "DIY Kits", "type": "diy_kit", "stock": 40, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_11", "name": "37-in-1 Sensor Kit", "slug": "37-in-1-sensor-kit", "description": "Massive sensor laboratory bundle with 37 essential sensor modules including ultrasonic, flame, sound, tilt, hall effect, infrared, and temperature modules in a sturdy organizer case.", "short_description": "Complete 37-Sensor Lab Module Pack for Arduino & ESP32", "price": 1450.0, "original_price": 1999.0, "category": "DIY Kits", "type": "diy_kit", "stock": 25, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_diy_12", "name": "Dual-Axis Solar Tracker Kit", "slug": "dual-axis-solar-tracker-kit", "description": "Dual-axis automatic solar panel orientation kit that rotates towards the brightest sunlight using four LDR light sensors and twin servo motors for maximum energy harvesting.", "short_description": "Dual-Axis Light-Seeking Solar Tracker Project Kit", "price": 1150.0, "original_price": 1599.0, "category": "DIY Kits", "type": "diy_kit", "stock": 20, "images": ["assets/images/products/solar_tracker_kit.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_sp1", "name": "Smart Dustbin Kit", "slug": "smart-dustbin-project", "description": "Top-selling school science fair exhibition project. Automatically opens the lid when hands approach within 20cm using an ultrasonic distance sensor and micro servo motor.", "short_description": "Touchless Automatic Smart Dustbin Project Kit", "price": 750.0, "original_price": 999.0, "category": "School Projects", "type": "electronics", "stock": 35, "images": ["assets/images/products/smart_dustbin_kit.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_sp2", "name": "Solar Tracker Project Kit", "slug": "solar-tracker-project", "description": "Dual-axis automatic solar panel orientation kit that rotates towards the brightest sunlight using four LDR light sensors and twin servo motors for maximum energy harvesting.", "short_description": "Dual-Axis Light-Seeking Solar Tracker Project", "price": 1150.0, "original_price": 1599.0, "category": "School Projects", "type": "electronics", "stock": 20, "images": ["assets/images/products/solar_tracker_kit.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_sp3", "name": "Smart Plant Watering Kit", "slug": "smart-plant-watering-kit", "description": "Automatic soil moisture sensing irrigation project. Detects dry soil and automatically activates a 5V mini water pump to water plants, with an alert buzzer when water tank is empty.", "short_description": "Automated Soil Moisture Irrigation Science Kit", "price": 680.0, "original_price": 899.0, "category": "School Projects", "type": "electronics", "stock": 28, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_rob1", "name": "4WD Robot Smart Chassis", "slug": "4wd-robot-smart-chassis", "description": "Durable laser-cut dual acrylic chassis with four high-torque BO gear motors, rubber grip wheels, speed encoder discs, battery container and complete mounting hardware.", "short_description": "Complete 4-Wheel Drive Robotics Base Chassis", "price": 499.0, "original_price": 699.0, "category": "Robotics", "type": "electronics", "stock": 40, "images": ["assets/images/products/smart_robot_car_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_rob2", "name": "4-DOF Metal Robotic Arm", "slug": "4-dof-metal-robotic-arm", "description": "Precision CNC-machined aluminum alloy robotic arm with 4 degrees of freedom. Powered by high torque MG996R metal gear servos for industrial pick-and-place automation.", "short_description": "All-Metal 4-Axis Robotic Arm Manipulator Kit", "price": 1850.0, "original_price": 2499.0, "category": "Robotics", "type": "electronics", "stock": 12, "images": ["assets/images/products/robotic_arm_4dof.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_rob3", "name": "Mechanical Gripper Claw", "slug": "mechanical-gripper-claw", "description": "Heavy duty aluminum mechanical robotic gripper claw compatible with standard MG995, MG996R, and SG90 servo horns for robot arm grasping.", "short_description": "Heavy-Duty Aluminum Robot Gripper Claw", "price": 320.0, "original_price": 450.0, "category": "Robotics", "type": "electronics", "stock": 45, "images": ["assets/images/products/robotic_arm_4dof.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_el1", "name": "MB-102 830-Point Breadboard", "slug": "mb-102-breadboard", "description": "High-durability solderless breadboard with 830 tie points and dual power distribution bus strips. Features self-adhesive back and interlocking tabs.", "short_description": "830 Tie-Point Solderless Prototyping Breadboard", "price": 140.0, "original_price": 199.0, "category": "Electronics", "type": "electronics", "stock": 80, "images": ["assets/images/products/arduino_uno_r3.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_el2", "name": "65pcs Jumper Wires Bundle", "slug": "65pcs-jumper-wires-bundle", "description": "Flexible multi-color male-to-male breadboard jumper wires with sturdy molded pins in assorted lengths (10cm, 15cm, 20cm, 25cm).", "short_description": "65-Piece Assorted Male-to-Male Jumper Wire Pack", "price": 99.0, "original_price": 150.0, "category": "Electronics", "type": "electronics", "stock": 95, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_el3", "name": "16x2 I2C LCD Display (Blue)", "slug": "16x2-i2c-lcd-display", "description": "High contrast 16-character by 2-line alphanumeric LCD display with pre-soldered I2C backpack interface. Saves Arduino pins by using only SDA and SCL.", "short_description": "1602 HD44780 LCD with Pre-Soldered I2C Serial Backpack", "price": 199.0, "original_price": 280.0, "category": "Electronics", "type": "electronics", "stock": 55, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_iot1", "name": "ESP32 NodeMCU Dev Board", "slug": "esp32-dev-board", "description": "Powerful dual-core 240MHz microcontroller with built-in Wi-Fi and Bluetooth BLE 4.2. Ideal for smart home automation, remote IoT sensor logging, and wearable connected devices.", "short_description": "Dual-Core 240MHz Wi-Fi + Bluetooth IoT Board", "price": 650.0, "original_price": 799.0, "category": "IoT & Smart", "type": "electronics", "stock": 30, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_iot2", "name": "NodeMCU ESP8266 Wi-Fi", "slug": "nodemcu-esp8266", "description": "Popular compact Wi-Fi enabled microcontroller board with integrated TCP/IP protocol stack. Perfect for wireless smart home switches and cloud sensor telemetry.", "short_description": "ESP8266 CP2102 Lua Wi-Fi Development Board", "price": 280.0, "original_price": 399.0, "category": "IoT & Smart", "type": "electronics", "stock": 45, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_iot3", "name": "HC-05 Bluetooth Module", "slug": "hc-05-bluetooth-module", "description": "Master and Slave 2-in-1 Bluetooth SPP (Serial Port Protocol) module for transparent wireless serial communication between Arduino and smartphones.", "short_description": "HC-05 Wireless Bluetooth Serial Transceiver Module", "price": 260.0, "original_price": 350.0, "category": "IoT & Smart", "type": "electronics", "stock": 35, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_b1", "name": "Arduino UNO R3", "slug": "arduino-uno-r3", "description": "The standard and most popular microcontroller board based on the ATmega328P. Features 14 digital I/O pins, 6 analog inputs, 16 MHz quartz crystal, and USB connection.", "short_description": "Standard ATmega328P Microcontroller Board for Makers", "price": 450.0, "original_price": 599.0, "category": "Dev Boards", "type": "electronics", "stock": 45, "images": ["assets/images/products/arduino_uno_r3.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_b2", "name": "Arduino Nano V3 (Type-C)", "slug": "arduino-nano-v3", "description": "Small, complete, and breadboard-friendly dev board based on the ATmega328P with modern USB Type-C connector. Works with all Arduino UNO libraries.", "short_description": "Breadboard-Friendly ATmega328P Nano Board with Type-C", "price": 240.0, "original_price": 320.0, "category": "Dev Boards", "type": "electronics", "stock": 60, "images": ["assets/images/products/arduino_nano_v3.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_b3", "name": "Raspberry Pi Pico W", "slug": "raspberry-pi-pico-w", "description": "Official Raspberry Pi RP2040 Dual-Core ARM Cortex-M0+ microcontroller with built-in 2.4GHz wireless interface. Programmable in C/C++ and MicroPython.", "short_description": "RP2040 Dual-Core ARM Microcontroller with 2.4GHz Wi-Fi", "price": 580.0, "original_price": 720.0, "category": "Dev Boards", "type": "electronics", "stock": 22, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_s1", "name": "HC-SR04 Ultrasonic Sensor", "slug": "hc-sr04-sensor", "description": "High-accuracy non-contact ultrasonic distance measuring module. Provides 2cm to 400cm measurement range with 3mm precision.", "short_description": "Ultrasonic Distance Measuring Sensor Module (2cm-400cm)", "price": 80.0, "original_price": 120.0, "category": "Sensors", "type": "electronics", "stock": 150, "images": ["assets/images/products/ultrasonic_sensor_hcsr04.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_s2", "name": "MPU6050 6-Axis Gyro", "slug": "mpu6050-gyro-sensor", "description": "Triple-axis MEMS gyroscope and triple-axis accelerometer with on-board Digital Motion Processor (DMP) communicating over I2C.", "short_description": "6-DOF Gyroscope + Accelerometer Sensor Module", "price": 150.0, "original_price": 210.0, "category": "Sensors", "type": "electronics", "stock": 50, "images": ["assets/images/products/ultrasonic_sensor_hcsr04.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_s3", "name": "DHT11 Temp & Humidity", "slug": "dht11-sensor", "description": "Calibrated digital output composite sensor for measuring ambient temperature and relative humidity with single-wire serial data transmission.", "short_description": "Digital Temperature & Relative Humidity Sensor Module", "price": 95.0, "original_price": 140.0, "category": "Sensors", "type": "electronics", "stock": 75, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_m1", "name": "TowerPro SG90 9g Servo", "slug": "sg90-servo-motor", "description": "Ultra-lightweight 180-degree analog micro servo with nylon gears, high speed, and standard 3-pin PWM connector.", "short_description": "9-Gram 180\\u00b0 Micro Servo Motor with Arms Pack", "price": 99.0, "original_price": 149.0, "category": "Motors & Drivers", "type": "electronics", "stock": 120, "images": ["assets/images/products/sg90_micro_servo.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_m2", "name": "L298N Dual Motor Driver", "slug": "l298n-motor-driver", "description": "High-power dual H-bridge motor driver board capable of driving two DC motors bidirectionally with PWM speed control or one 4-wire stepper motor up to 2A.", "short_description": "Dual H-Bridge DC & Stepper Motor Driver Controller Board", "price": 160.0, "original_price": 240.0, "category": "Motors & Drivers", "type": "electronics", "stock": 65, "images": ["assets/images/products/smart_robot_car_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_m3", "name": "MG996R Metal Gear Servo", "slug": "mg996r-servo", "description": "Heavy duty high-torque metal gear servo motor offering up to 11 kg/cm torque. Upgraded internal PCB with smooth dual ball bearing output shaft.", "short_description": "11kg/cm High-Torque All-Metal Gear Standard Servo", "price": 340.0, "original_price": 480.0, "category": "Motors & Drivers", "type": "electronics", "stock": 40, "images": ["assets/images/products/robotic_arm_4dof.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_mod1", "name": "4-Channel 5V Relay Board", "slug": "4-channel-relay-module", "description": "High-current 4-channel relay interface board equipped with optocoupler isolation. Allows low-voltage microcontrollers to safely switch 250V AC mains loads.", "short_description": "4-Channel 5V Optocoupler Relay Module (10A 250V AC)", "price": 170.0, "original_price": 240.0, "category": "Modules", "type": "electronics", "stock": 50, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_mod2", "name": "RC522 RFID Kit + Cards", "slug": "rc522-rfid-module", "description": "13.56MHz contactless RFID reader and writer module communicating over high-speed SPI. Includes smart card and keyfob transponder.", "short_description": "13.56MHz MFRC-522 RFID Reader/Writer + Tag Kit", "price": 145.0, "original_price": 210.0, "category": "Modules", "type": "electronics", "stock": 60, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_mod3", "name": "0.96 inch I2C OLED Display", "slug": "0-96-oled-display", "description": "Ultra-crisp 128x64 self-luminous white OLED graphic display module. Requires only 4 pins (VCC, GND, SCL, SDA) for high-speed I2C communication.", "short_description": "128x64 White I2C OLED Screen Module (SSD1306)", "price": 220.0, "original_price": 310.0, "category": "Modules", "type": "electronics", "stock": 45, "images": ["assets/images/products/esp32_iot_smart_home.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_cmp1", "name": "300pcs Resistor Kit (30 Val)", "slug": "300pcs-resistor-kit", "description": "Comprehensive 1/4W 1% metal film resistor assortment containing 10 pieces each of 30 standard resistance values from 10\\u03a9 up to 1M\\u03a9.", "short_description": "300-Piece 1/4W 1% Metal Film Resistor Assortment Kit", "price": 180.0, "original_price": 260.0, "category": "Components", "type": "electronics", "stock": 110, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_cmp2", "name": "100pcs 5mm Multi-Color LEDs", "slug": "100pcs-5mm-led-kit", "description": "Bright 5mm diffused LED assortment box featuring 20 pieces each of Red, Green, Blue, Yellow, and White light-emitting diodes.", "short_description": "100-Piece 5mm Diffused LED Pack in 5 Vibrant Colors", "price": 120.0, "original_price": 180.0, "category": "Components", "type": "electronics", "stock": 90, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_t1", "name": "60W Adjustable Soldering Kit", "slug": "60w-soldering-iron-kit", "description": "Complete professional electronics soldering station kit featuring 60W temperature adjustable soldering iron (200\\u00b0C - 450\\u00b0C), stand, desoldering pump, solder wire, 5 interchangeable tips & anti-static tweezers.", "short_description": "60W Temp-Controlled Soldering Station & Tool Pack", "price": 699.0, "original_price": 999.0, "category": "Tools & Acc.", "type": "electronics", "stock": 35, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_t2", "name": "Digital Multimeter XL830L", "slug": "digital-multimeter-xl830l", "description": "Essential digital test multimeter with backlit LCD screen, continuity buzzer, diode tester, and rubber protective shockproof casing with fold-out kickstand.", "short_description": "Digital AC/DC Voltage, Current & Continuity Multimeter", "price": 350.0, "original_price": 499.0, "category": "Tools & Acc.", "type": "electronics", "stock": 45, "images": ["assets/images/products/solar_tracker_kit.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_3d1", "name": "PLA+ 1.75mm Filament (1kg)", "slug": "pla-plus-1-75mm-filament", "description": "Premium dimensional accuracy (\\u00b10.02mm) PLA+ 3D printing filament. Enhanced toughness, low odor, smooth layer adhesion, zero warping on standard heated beds.", "short_description": "High-Strength 1.75mm PLA+ 3D Printer Filament Spool 1kg", "price": 899.0, "original_price": 1299.0, "category": "3D Printing", "type": "electronics", "stock": 25, "images": ["assets/images/products/robotic_arm_4dof.jpg"], "is_active": true, "linked_course_id": null}, {"id_str": "prod_3d2", "name": "MK8 0.4mm Brass Nozzles (5pcs)", "slug": "mk8-brass-nozzles-5pcs", "description": "High-precision CNC machined 0.4mm M6 brass extruder nozzles for smooth flow and sharp detailing. Compatible with Ender 3, CR-10, Anet & Edukkit 3D printers.", "short_description": "Pack of 5 Precision 0.4mm M6 MK8 Extruder Nozzles", "price": 120.0, "original_price": 190.0, "category": "3D Printing", "type": "electronics", "stock": 60, "images": ["assets/images/products/electronics_starter_kit.png"], "is_active": true, "linked_course_id": null}]')

def generate_lessons_for_course(course_title, category):
    """Generates 9 structured lessons per course matching Flutter courses_data.dart."""
    is_junior_robotics = "junior robotics" in course_title.lower()
    
    topic = "Robotics"
    if "electr" in course_title.lower():
        topic = "Electronics"
    elif "3d" in course_title.lower():
        topic = "3D Printing"
    elif "ai" in course_title.lower():
        topic = "AI"
    elif "iot" in course_title.lower():
        topic = "IoT & Smart Tech"

    lessons = [
        {
            "order_index": 1,
            "title": f"Introduction to {course_title}",
            "description": f"Overview of {course_title} fundamentals, tools, and roadmap.",
            "duration": 165 if is_junior_robotics else 195,
            "is_free_preview": True,
            "video_stream_id": "bcdd59aa-1332-4a20-bb30-6dbdbaf0d386" if is_junior_robotics else f"bunny_stream_{topic.lower()}_01",
            "notes_pdf": "assets/docs/starter_guide.pdf",
            "circuit_diagram": "assets/docs/starter_schematic.pdf",
        },
        {
            "order_index": 2,
            "title": "How this course works",
            "description": "Learning path, project milestones, and hands-on kit usage instructions.",
            "duration": 252,
            "is_free_preview": True,
            "video_stream_id": f"bunny_stream_{topic.lower()}_02",
            "notes_pdf": "assets/docs/course_overview.pdf",
            "circuit_diagram": None,
        },
        {
            "order_index": 3,
            "title": "Your first hands-on activity",
            "description": "Unboxing hardware components, safety rules, and initial setup.",
            "duration": 398,
            "is_free_preview": True,
            "video_stream_id": f"bunny_stream_{topic.lower()}_03",
            "notes_pdf": "assets/docs/activity_1.pdf",
            "circuit_diagram": "assets/docs/wiring_diagram_1.pdf",
        },
        {
            "order_index": 4,
            "title": f"Core Fundamentals of {topic}",
            "description": f"Deep dive into the core concepts and theoretical foundations of {topic}.",
            "duration": 509,
            "is_free_preview": False,
            "video_stream_id": f"bunny_stream_{topic.lower()}_04",
            "notes_pdf": "assets/docs/theory_notes.pdf",
            "circuit_diagram": None,
        },
        {
            "order_index": 5,
            "title": "Essential Components & Tools",
            "description": "Understanding sensors, controllers, wiring, and measurement instruments.",
            "duration": 555,
            "is_free_preview": False,
            "video_stream_id": f"bunny_stream_{topic.lower()}_05",
            "notes_pdf": "assets/docs/components_datasheet.pdf",
            "circuit_diagram": "assets/docs/schematic_2.pdf",
        },
        {
            "order_index": 6,
            "title": "Intermediate Hands-on Lab",
            "description": "Building practical circuits, writing firmware, and testing subsystems.",
            "duration": 702,
            "is_free_preview": False,
            "video_stream_id": f"bunny_stream_{topic.lower()}_06",
            "notes_pdf": "assets/docs/lab_manual.pdf",
            "circuit_diagram": "assets/docs/circuit_diagram_3.pdf",
        },
        {
            "order_index": 7,
            "title": "Building Your Practical Project",
            "description": "Assembling the full hardware system and integrating software modules.",
            "duration": 1110,
            "is_free_preview": False,
            "video_stream_id": f"bunny_stream_{topic.lower()}_07",
            "notes_pdf": "assets/docs/assembly_guide.pdf",
            "circuit_diagram": "assets/docs/full_system_wiring.pdf",
        },
        {
            "order_index": 8,
            "title": "Testing & Troubleshooting",
            "description": "Debugging common connection errors, signal analysis, and optimization.",
            "duration": 845,
            "is_free_preview": False,
            "video_stream_id": f"bunny_stream_{topic.lower()}_08",
            "notes_pdf": "assets/docs/troubleshooting.pdf",
            "circuit_diagram": None,
        },
        {
            "order_index": 9,
            "title": "Final Capstone Project",
            "description": "Demonstration of the completed project, customization ideas, and certification.",
            "duration": 1520,
            "is_free_preview": False,
            "video_stream_id": f"bunny_stream_{topic.lower()}_09",
            "notes_pdf": "assets/docs/capstone_project.pdf",
            "circuit_diagram": "assets/docs/final_schematic.pdf",
        },
    ]
    return lessons


def seed_db():
    """
    IDEMPOTENT Production/Development Catalog Seeder.
    Creates missing courses, lessons, and products without duplicating or overwriting data.
    NEVER deletes orders, users, payments, entitlements, or modified prices.
    """
    print("Verifying database schema...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Pre-seed counts
        print("Pre-seed Database Audit:")
        print(f"  Courses: {db.query(Course).count()}")
        print(f"  Lessons: {db.query(Lesson).count()}")
        print(f"  Products: {db.query(Product).count()}")
        print(f"  Orders: {db.query(Order).count()}")
        print(f"  Payments: {db.query(Payment).count()}")
        print(f"  Entitlements: {db.query(CourseEntitlement).count()}")
        print(f"  Users: {db.query(User).count()}")

        # 1. Seed Courses & Lessons
        print("\nSeeding 13 Approved Courses...")
        course_map = {}
        for cdata in COURSES_DATA:
            existing = db.query(Course).filter(Course.title == cdata["title"]).first()
            if not existing:
                course = Course(
                    title=cdata["title"],
                    description=cdata["description"],
                    short_description=cdata["short_description"],
                    thumbnail=cdata["thumbnail"],
                    price=cdata["price"],
                    original_price=cdata["original_price"],
                    category=cdata["category"],
                    level=cdata["level"],
                    instructor=cdata["instructor"],
                    bunny_collection_id=cdata.get("bunny_collection_id"),
                    is_published=True,
                    is_free=cdata.get("is_free", False),
                )
                db.add(course)
                db.commit()
                db.refresh(course)
                print(f"  [+] Created Course: {course.title} (ID: {course.id})")
                existing = course
            else:
                print(f"  [.] Course already exists: {existing.title} (ID: {existing.id})")
            
            course_map[existing.title] = existing.id

            # Seed Lessons for this course
            lessons_to_seed = generate_lessons_for_course(existing.title, existing.category)
            for ldata in lessons_to_seed:
                existing_lesson = db.query(Lesson).filter(
                    Lesson.course_id == existing.id,
                    Lesson.order_index == ldata["order_index"],
                ).first()
                if not existing_lesson:
                    lesson = Lesson(
                        course_id=existing.id,
                        title=ldata["title"],
                        description=ldata["description"],
                        video_stream_id=ldata["video_stream_id"],
                        duration=ldata["duration"],
                        notes_pdf=ldata["notes_pdf"],
                        circuit_diagram=ldata["circuit_diagram"],
                        order_index=ldata["order_index"],
                        is_free_preview=ldata["is_free_preview"],
                    )
                    db.add(lesson)
                else:
                    # Keep metadata accurate
                    existing_lesson.is_free_preview = ldata["is_free_preview"]
                    if ldata["video_stream_id"]:
                        existing_lesson.video_stream_id = ldata["video_stream_id"]
                    if ldata["notes_pdf"]:
                        existing_lesson.notes_pdf = ldata["notes_pdf"]
                    if ldata["circuit_diagram"]:
                        existing_lesson.circuit_diagram = ldata["circuit_diagram"]
            db.commit()

        # 2. Seed Store Products
        print("\nSeeding 45 Store Products...")
        for pdata in PRODUCTS_DATA:
            existing_prod = db.query(Product).filter(Product.name == pdata["name"]).first()
            
            # Map linked course ID if applicable
            linked_cid = None
            if pdata.get("linked_course_id") or "smart obstacle avoiding car" in pdata["name"].lower():
                linked_cid = course_map.get("Junior Robotics Engineer")

            if not existing_prod:
                prod = Product(
                    name=pdata["name"],
                    description=pdata["description"],
                    price=pdata["price"],
                    original_price=pdata["original_price"],
                    stock=pdata["stock"],
                    images=json.dumps(pdata["images"]),
                    category=pdata["category"],
                    type=pdata["type"],
                    is_active=True,
                    linked_course_id=linked_cid,
                )
                db.add(prod)
                print(f"  [+] Created Product: {prod.name} ({prod.category})")
            else:
                print(f"  [.] Product already exists: {existing_prod.name} ({existing_prod.category})")

        db.commit()
        print("\nSeeding complete!")

        # Post-seed counts
        print("\nPost-seed Database Audit:")
        print(f"  Courses: {db.query(Course).count()}")
        print(f"  Lessons: {db.query(Lesson).count()}")
        print(f"  Products: {db.query(Product).count()}")
        print(f"  Orders: {db.query(Order).count()}")
        print(f"  Payments: {db.query(Payment).count()}")
        print(f"  Entitlements: {db.query(CourseEntitlement).count()}")
        print(f"  Users: {db.query(User).count()}")

    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
