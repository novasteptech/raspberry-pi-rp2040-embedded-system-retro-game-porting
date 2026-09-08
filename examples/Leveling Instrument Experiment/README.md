# 基于RP2040开发板


## 功能设计

1. 屏幕显示以中心为原点的十字坐标, 红色方块显示当前姿态
2. 以数值显示当前X/Y/Z方向坐标
3. 按B键锁定当前姿态, 屏幕显示空心蓝色方块, 之后移动显示实时姿态, 再次按B键清除锁定姿态数据


## 涉及硬件及所需基本功能

1. 屏幕 ST7789
    - 绘制基本图形(圆, 矩形, 空心/实心)
    - 绘制文字
2. IMU MMA7660
    - 读取三轴X/Y/Z数据
    - 6Bit精度, 3个刻度的误差, 需经均值滤波(8val或32阶)
3. 按键
    - 获取按键按下状态
    - 软件消抖


## 变量/函数说明

变量

```
imu MMA7660实例
lcd ST7789实例
curr_x, curr_y 本周期的位置
last_x, last_y 上周期的位置
stor_x, stor_y 存储的位置
stor_flag   是否有存储
```

函数
```
imu.getXYZ() 返回当前位置
lcd.rect() 画矩形
lcd.text() 画线

get_key()
draw_bg(lcd)
draw_legend(lcd)
draw_box(lcd, center_x, center_y, size, color, thick=1, fill=False)
draw_number(lcd, a_x, a_y, b_x, b_y, stor_flag)
calc_degree(imu_val)

```

## 参考

- 固件: https://github.com/russhughes/st7789_mpy
- 平均滤波: https://github.com/peterhinch/micropython-filters