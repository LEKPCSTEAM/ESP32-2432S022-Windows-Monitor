/*
    board: ESP32-2432S022 
*/

#include <Arduino.h>
#include <lvgl.h>  // v. 8.3.11
#include "demos/lv_demos.h"
#include "CST820.h"  // Capacitive touch controller

#define TFT_WIDTH 320
#define TFT_HEIGHT 240

#define I2C_SDA 21
#define I2C_SCL 22

#define GFX
#define TOUCH

// Global LVGL objects
lv_obj_t *bar_cpu, *bar_ram, *bar_disk, *bar_temp, *bar_gpu;
lv_obj_t *label_cpu, *label_disk, *label_ram, *label_temp, *label_gpu;

#ifdef TOUCH
CST820 touch(I2C_SDA, I2C_SCL, -1, -1);  // Touch instance
#endif

static lv_disp_draw_buf_t draw_buf;
lv_indev_t *myInputDevice;

#if defined(GFX)
#define LGFX_USE_V1
#include <LovyanGFX.hpp>  // v.1.2.7

class LGFX : public lgfx::LGFX_Device {
  lgfx::Panel_ST7789 _panel_instance;
  lgfx::Bus_Parallel8 _bus_instance;

public:
  LGFX(void) {
    {
      auto cfg = _bus_instance.config();
      cfg.freq_write = 25000000;
      cfg.pin_wr = 4;
      cfg.pin_rd = 2;
      cfg.pin_rs = 16;
      cfg.pin_d0 = 15;
      cfg.pin_d1 = 13;
      cfg.pin_d2 = 12;
      cfg.pin_d3 = 14;
      cfg.pin_d4 = 27;
      cfg.pin_d5 = 25;
      cfg.pin_d6 = 33;
      cfg.pin_d7 = 32;
      _bus_instance.config(cfg);
      _panel_instance.setBus(&_bus_instance);
    }

    {
      auto cfg = _panel_instance.config();
      cfg.pin_cs = 17;
      cfg.pin_rst = -1;
      cfg.pin_busy = -1;
      cfg.panel_width = 240;   // real panel width
      cfg.panel_height = 320;  // real panel height
      cfg.offset_x = 0;
      cfg.offset_y = 0;
      cfg.readable = false;
      cfg.invert = false;
      cfg.rgb_order = false;
      cfg.dlen_16bit = false;
      cfg.bus_shared = true;
      _panel_instance.config(cfg);
    }
    setPanel(&_panel_instance);
  }
};

static LGFX tft;

// LVGL flush callback to transfer rendered area to display
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
  int w = (area->x2 - area->x1 + 1);
  int h = (area->y2 - area->y1 + 1);
  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, w, h);
  tft.writePixels(&color_p->full, w * h, false);
  tft.endWrite();
  lv_disp_flush_ready(disp);
}

#ifdef TOUCH
// Adjust touch X/Y according to screen rotation
void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data) {
  bool touched;
  uint8_t gesture;
  uint16_t touchX, touchY;

  touched = touch.getTouch(&touchX, &touchY, &gesture);
  if (!touched) {
    data->state = LV_INDEV_STATE_REL;
    return;
  }
  data->state = LV_INDEV_STATE_PR;

  uint8_t rot = tft.getRotation();
  switch (rot) {
    case 0:
      data->point.x = touchX;
      data->point.y = touchY;
      break;
    case 1:
      data->point.x = touchY;
      data->point.y = TFT_HEIGHT - touchX;
      break;
    case 2:
      data->point.x = TFT_WIDTH - touchX;
      data->point.y = TFT_HEIGHT - touchY;
      break;
    case 3:
      data->point.x = TFT_WIDTH - touchY;
      data->point.y = touchX;
      break;
    default:
      data->point.x = touchX;
      data->point.y = touchY;
      break;
  }
}
#endif
#endif

// Create the bar + label UI
void create_stat_screen() {
  lv_obj_t *title = lv_label_create(lv_scr_act());
  lv_label_set_text(title, "System Monitor");
  lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);

  // Bar/label creation shortened for brevity. (same as previous)
  // CPU, RAM, DISK, TEMP, GPU
  // ...
}

void setup() {
  Serial.begin(115200);
  pinMode(0, OUTPUT);
  digitalWrite(0, HIGH);

#ifdef TOUCH
  touch.begin();
#endif

#if defined(GFX)
  lv_init();
  tft.init();
  tft.setRotation(1);  // Rotate screen 90 degrees clockwise

  lv_color_t *buf1 = (lv_color_t *)heap_caps_malloc(TFT_WIDTH * 40 * sizeof(lv_color_t), MALLOC_CAP_DMA);
  lv_color_t *buf2 = (lv_color_t *)heap_caps_malloc(TFT_WIDTH * 40 * sizeof(lv_color_t), MALLOC_CAP_DMA);
  lv_disp_draw_buf_init(&draw_buf, buf1, buf2, TFT_WIDTH * 40);

  static lv_disp_drv_t disp_drv;
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = TFT_WIDTH;
  disp_drv.ver_res = TFT_HEIGHT;
  disp_drv.flush_cb = my_disp_flush;
  disp_drv.draw_buf = &draw_buf;
  lv_disp_drv_register(&disp_drv);

#ifdef TOUCH
  static lv_indev_drv_t indev_drv;
  lv_indev_drv_init(&indev_drv);
  indev_drv.type = LV_INDEV_TYPE_POINTER;
  indev_drv.read_cb = my_touchpad_read;
  lv_indev_drv_register(&indev_drv);
#endif

  tft.fillScreen(TFT_BLACK);
  create_stat_screen();
#endif
}

// Update LVGL values from received serial data
void update_stats(float cpu, float ram, float disk, float temp, float gpu) {
  char buf[16];
  lv_bar_set_value(bar_cpu, cpu, LV_ANIM_OFF);
  snprintf(buf, sizeof(buf), "%.1f%%", cpu);
  lv_label_set_text(label_cpu, buf);

  lv_bar_set_value(bar_ram, ram, LV_ANIM_OFF);
  snprintf(buf, sizeof(buf), "%.1f%%", ram);
  lv_label_set_text(label_ram, buf);

  lv_bar_set_value(bar_disk, disk, LV_ANIM_OFF);
  snprintf(buf, sizeof(buf), "%.1f%%", disk);
  lv_label_set_text(label_disk, buf);

  lv_bar_set_value(bar_temp, temp, LV_ANIM_OFF);
  snprintf(buf, sizeof(buf), "%.1fC", temp);
  lv_label_set_text(label_temp, buf);

  lv_bar_set_value(bar_gpu, gpu, LV_ANIM_OFF);
  snprintf(buf, sizeof(buf), "%.1f%%", gpu);
  lv_label_set_text(label_gpu, buf);
}

void loop() {
  lv_timer_handler();
  delay(5);

  static char buffer[64];
  static uint8_t idx = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      buffer[idx] = '\0';
      float cpu, ram, disk, temp, gpu;
      sscanf(buffer, "%f,%f,%f,%f,%f", &cpu, &ram, &disk, &temp, &gpu);
      update_stats(cpu, ram, disk, temp, gpu);
      idx = 0;
    } else if (idx < sizeof(buffer) - 1) {
      buffer[idx++] = c;
    }
  }
}
