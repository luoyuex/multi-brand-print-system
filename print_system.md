# 🧾 商品录单 + 多品牌打印系统（Vue + Element Plus + Electron）

## 一、项目概述

本系统是一个面向门店/批发/配送场景的高频录单 + 本地自动打印系统。

核心能力：
- 多品牌商品体系
- 商品快速录入（序号 / 名称搜索）
- 订单打印
- 手动改价
- Electron 本地打印服务
- 多模板打印

---

## 二、系统架构

Vue（PC/平板）
    ↓
后端 API（PHP/Node）
    ↓
Electron PrintService（本地）
    ↓
打印机

---

## 三、核心数据模型

### 1. 品牌 Brand
{
  "id": 1,
  "name": "MISS"
}

### 2. 商品 Product
{
  "id": 1,
  "brandId": 1,
  "code": "1",
  "name": "西瓜",
  "spec": "个",
  "price": 1.8
}

### 3. 打印单 Order
{
  "brandId": 1,
  "customer": "客户A",
  "items": [
    {
      "code": "1",
      "name": "西瓜",
      "qty": 10,
      "price": 1.8,
      "manualPrice": false
    }
  ]
}

---

## 四、核心功能

### 1. 品牌切换
切换品牌 = 切换商品体系

### 2. 商品选择（Element Plus）
支持：
- 序号输入
- 名称搜索
- 模糊匹配

### 3. 快速录单流程
输入商品 → 输入数量 → 回车加入订单

### 4. 改价逻辑
- 默认用商品价格
- 支持手动修改

---

## 五、Electron 打印服务

PrintService.exe

功能：
- HTTP/WebSocket 接口
- 打印队列
- 模板渲染（HTML）
- 打印机管理
- 系统托盘

---

## 六、打印流程

Vue
 → API
 → PrintService.exe
 → 打印机

---

## 七、模板方案（推荐HTML）

<h2>{{brandName}} 发货单</h2>
客户：{{customer}}

{{#each items}}
{{code}} {{name}} {{qty}} {{price}}
{{/each}}

---

## 八、技术栈

前端：Vue3 + Element Plus
后端：Node / PHP
桌面：Electron
数据库：MySQL
