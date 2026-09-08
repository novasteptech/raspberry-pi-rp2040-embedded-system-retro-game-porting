"""
基于RP2040开发板的水平仪 By BI3QXJ(老韩)

- 功能设计

1. 屏幕显示以中心为原点的十字坐标, 红色正方形显示当前姿态
2. 以数值显示当前X/Y方向坐标
3. 按A键锁定当前姿态, 屏幕显示空心蓝色正方形(固定位置), 再按A键清除锁定姿态数据

- 常量
各Pin脚
LCD_W = 240
LCD_H = 240

BOX_A_H = 20
BOX_A_H = 20

- 变量
imu MMA7660实例
lcd ST7789实例
curr_pos = [x, y, _] 当前姿态 X/Y/Z值
stor_pos = [x, y, _] 存储姿态 X/Y/Z值
stor_stat = true/false 是否显示存储姿态

- 函数说明
x, y, z = get_imu_value() 返回当前姿态(-90° ~ +90°)
btn_A, btn_B = get_key_value() 返回当前按键状态

```

##
"""
import time
import array
import random
from machine import Pin, SPI, ADC, I2C
import st7789
import mma7660
from avg_pico import avg
from time import ticks_ms, ticks_diff

# import vga1_8x8 as font1a
import vga1_8x16 as font1b

import utime

LCD_RST = 0      # ST7789
LCD_DC = 1
LCD_SCK = 2
LCD_SDA = 3
LED_STA = 4      # 背面LED灯
BTN_B = 5        # 按键
BTN_A = 6
BTN_START = 7 
BTN_SELECT = 8
IMU_INT = 9      # MMA7660
IMU_SDA = 10
IMU_SCL = 11
BUZZER = 23      # 蜂鸣器
IR_TX = 24       # 红外线收发管
IR_RX = 25
JOYSTICK_X = 28  # 摇杆
JOYSTICK_Y = 29

def get_key():
    """读取按键和摇杆状态"""
    buttonB = Pin(BTN_B, Pin.IN, Pin.PULL_UP)
    buttonA = Pin(BTN_A, Pin.IN, Pin.PULL_UP)
    buttonStart = Pin(BTN_START, Pin.IN, Pin.PULL_UP) 
    buttonSelect = Pin(BTN_SELECT, Pin.IN, Pin.PULL_UP) 
    return {
        'A': buttonA.value(),
        'B': buttonB.value(),
        'START': buttonStart.value(),
        'SELECT': buttonSelect.value()
    }

# def get_joystick():
#     """获取摇杆状态"""
#     xAxis = ADC(Pin(JOYSTICK_X))
#     yAxis = ADC(Pin(JOYSTICK_Y))
#     return {
#         'X': xAxis.read_u16(),
#         'Y': yAxis.read_u16()
#     }

def imu_init():
    """初始化MMA7660并返回实例"""
    i2c1 = I2C(1, scl=Pin(IMU_SCL), sda=Pin(IMU_SDA))
    imu = mma7660.MMA7660(i2c1)
    imu.on(True)
    return imu

def lcd_init():
    """初始化并返回屏幕实例"""
    rt = Pin(LCD_RST, Pin.OUT)
    dc = Pin(LCD_DC, Pin.OUT)
    tx = Pin(LCD_SDA)
    sck = Pin(LCD_SCK)
    spi = SPI(0, baudrate=4000000, phase=1, polarity=1, sck=sck, mosi=tx)
    # 弥补驱动bug
    spi.write(bytes(0xff))
    rt.on()
    # 初始化屏幕
    lcd = st7789.ST7789(spi, 240, 240, reset=rt, dc=dc, rotation=0)
    lcd.init()
    return lcd

def draw_bg(lcd):
    # 绘制坐标轴
    lcd.hline(0, 119, 240, st7789.color565(255, 100, 255))
    lcd.hline(0, 120, 240, st7789.color565(255, 100, 255))
    lcd.vline(119, 0, 240, st7789.color565(100, 255, 255))
    lcd.vline(120, 0, 240, st7789.color565(100, 255, 255))
    # 外框
    lcd.rect(49, 49, 142, 142, st7789.GREEN)
    lcd.rect(50, 50, 140, 140, st7789.GREEN)
    # 坐标轴
    lcd.text(font1b, "x", 3, 103, st7789.color565(255, 100, 255))
    lcd.text(font1b, "y", 108, 223, st7789.color565(100, 255, 255))

def draw_legend(lcd):
    # 绘制数值区标识
    lcd.text(font1b, "X", 2, 207, st7789.color565(255, 255, 255))
    lcd.text(font1b, "Y", 2, 223, st7789.color565(255, 255, 255))
    lcd.text(font1b, "1", 27, 191, st7789.color565(255, 0, 0))
    lcd.text(font1b, "2", 57, 191, st7789.color565(0, 0, 255))
    lcd.line(85, 203, 95, 203, st7789.color565(255, 255, 255))
    lcd.line(85, 203, 93, 195, st7789.color565(255, 255, 255))

def calc_degree(imu_val):
    """传感器数值, 由于结果非线性, 在转为角度时进行分段近似计算"""
    if abs(imu_val) > 20:
        return imu_val * 4
    elif abs(imu_val) > 16:
        return imu_val * 3.5
    elif abs(imu_val) > 12:
        return imu_val * 3.2
    elif abs(imu_val) > 8:
        return imu_val * 3
    else:
        return imu_val * 2.9
    
def draw_number(lcd, a_x, a_y, b_x, b_y, stor_flag):
    """计算并绘制左下角的数值, 数字按右对齐, 覆盖黑矩形然后重绘数值"""
    lcd.fill_rect(15, 207, 60, 223, st7789.BLACK)
    lcd.text(font1b, "{:>3}".format(str(int(a_x))), 15, 207, st7789.color565(255, 255, 255))
    lcd.text(font1b, "{:>3}".format(str(int(a_y))), 15, 223, st7789.color565(255, 255, 255))
    if stor_flag:
        lcd.text(font1b, "{:>3}".format(str(int(b_x))), 45, 207, st7789.color565(255, 255, 255))
        lcd.text(font1b, "{:>3}".format(str(int(b_y))), 45, 223, st7789.color565(255, 255, 255))
        # 计算角度差值
        lcd.text(font1b, "{:>3}".format(str(int(abs(a_x - b_x)))), 75, 207, st7789.color565(255, 255, 255))
        lcd.text(font1b, "{:>3}".format(str(int(abs(a_y - b_y)))), 75, 223, st7789.color565(255, 255, 255))
    else:
        # 存储值和差值全没有
        lcd.text(font1b, '  -', 45, 207, st7789.color565(255, 255, 255))
        lcd.text(font1b, '  -', 45, 223, st7789.color565(255, 255, 255))
        lcd.text(font1b, '  -', 75, 207, st7789.color565(255, 255, 255))
        lcd.text(font1b, '  -', 75, 223, st7789.color565(255, 255, 255))

def draw_box(lcd, center_x, center_y, size, color, thick=1, fill=False):
    """绘制矩形, center/xy为中心坐标, size为边长, thick为边宽(仅对非填充生效, 向内填充), fill为是否填充"""
    if fill:
        lcd.fill_rect(center_x - size // 2, center_y - size // 2, size, size, color)
    else:
        for i in range(thick):
            lcd.rect(center_x - size // 2 + i, center_y - size // 2 + i, size - i * 2, size - i * 2, color)

def main():
    # 初始化硬件, 准备变量
    lcd = lcd_init()
    imu = imu_init()
    lcd.fill(st7789.BLACK)
    curr_x = last_x = 0
    curr_y = last_y = 0
    stor_x = 0
    stor_y = 0
    stor_flag = False
    
    # 准备均值平均所需列表
    arr_x = array.array('i', (0 for _ in range(19))) # Average over 16 samples
    arr_x[0] = len(arr_x)
    arr_y = array.array('i', (0 for _ in range(19))) # Average over 16 samples
    arr_y[0] = len(arr_y)
    
    # 准备消抖计时器
    t = ticks_ms()
    
    while True:
        # 获取当前姿态信息, 由于芯片安装方向与实际观察方向不一致, 坐标在这里调整
        curr_y, curr_x, _ = imu.getXYZ()      
        curr_x += 1  # 偏移一点
        curr_y += 0
        
        # 均值滤波
        curr_x = avg(arr_x, curr_x, 4)
        curr_y = avg(arr_y, curr_y, 4)
#         print(curr_x, curr_y)
        
        # 获取当前按键状态, 获取B键状态, 0=按下, 1=未按下
        btn_stat = get_key()
        button_b = btn_stat['B']
        if button_b == 0 and ticks_diff(ticks_ms(), t) > 300:
            if stor_flag == False:       # 若之前未存储
                stor_x, stor_y = curr_x, curr_y
            else:                        # 之前已存储, 这里覆盖消除
                draw_box(lcd, 120 - 2 * stor_x, 120 + 2 * stor_y, 60, st7789.BLACK, thick=1)
            
            # 翻转存储状态, 记录按下时间, 用于消抖
            stor_flag = not stor_flag
            t = ticks_ms()

        # 若比较不同则进行重绘, 绘制顺序: 底图, 存储方块, 活动方块, 数值区, 指示条
        if last_x != curr_x or last_y != last_y:
            draw_bg(lcd)
            draw_legend(lcd)
            draw_number(lcd, calc_degree(curr_x), calc_degree(curr_y), calc_degree(stor_x), calc_degree(stor_y), stor_flag)
            draw_box(lcd, 120 - 2 * last_x, 120 + 2 * last_y, 60, st7789.BLACK)
            draw_box(lcd, 120 - 2 * curr_x, 120 + 2 * curr_y, 60, st7789.RED, thick=1)
            if stor_flag:
                draw_box(lcd, 120 - 2 * stor_x, 120 + 2 * stor_y, 60, st7789.BLUE, thick=1)

            # 记录本次姿态数据, 下次若不变则不再重绘
            last_x, last_y = curr_x, curr_y
        time.sleep(0.02)

if __name__ == '__main__':
    main()
