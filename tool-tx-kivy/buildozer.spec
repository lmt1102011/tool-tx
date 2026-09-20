[app]
# Tên package + tên hiển thị
title = Tool TX
package.name = tooltx
package.domain = org.lmt1102011

source.dir = .
source.include_exts = py,kv,txt,png
version = 1.0.0

# Icon app (launcher)
icon.filename = icon-512.png
# Android
requirements = python3,kivy==2.3.0,kivymd==1.2.0,python-socketio==5.13.0,python-engineio==4.10.1,bidict==0.23.1,websocket-client==1.8.0,requests==2.32.3,pyjnius,android

orientation = portrait
fullscreen = 0

android.archs = arm64-v8a,x86_64
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.ndk = 25b
android.accept_sdk_license = True
p4a.branch = v2024.01.21
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# iOS (chưa dùng)
ios.kivy_ios_url = https://github.com/kivy/kivy-ios