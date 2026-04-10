---
title: Pion WebRTC для звонков
type: concept
created: 2026-04-11
updated: 2026-04-11
sources: [seed/messenger_test]
project: messenger
tags: [messenger, webrtc, pion, voip, sfu, coturn, calls]
---

# Pion WebRTC для звонков

[[entities/pulse-messenger|Pulse Messenger]] использует Pion WebRTC v4 для реализации голосовых и видеозвонков. Pion — чисто Go-реализация WebRTC, что позволяет интегрировать медиа-обработку непосредственно в серверный бинарник без внешних зависимостей на C/C++ библиотеки.

## Key Points

- Pion WebRTC v4.2.11 — полная Go-реализация WebRTC стека
- SFU (Selective Forwarding Unit) архитектура для групповых звонков
- COTURN v4.6 для NAT traversal (TURN/STUN сервер)
- DTLS v3 + SRTP v3 для шифрования медиа-потоков
- ICE v4 для установки peer-to-peer соединений
- Полный стек: signaling (WebSocket) → ICE/STUN/TURN → DTLS → SRTP → медиа

## Details

### Почему Pion, а не медиасервер

Альтернативы для WebRTC в бэкенде: Janus, mediasoup, LiveKit. Pion выбран потому что это нативная Go-библиотека, которая компилируется в тот же бинарник что и остальной сервер. Нет необходимости в отдельном медиасервере, что упрощает деплой и снижает операционную сложность. Для мессенджера с SFU-архитектурой Pion предоставляет достаточную гибкость.

### SFU-архитектура

Для групповых звонков используется SFU (Selective Forwarding Unit), а не MCU (Multipoint Control Unit). SFU пересылает медиа-потоки между участниками без перекодирования, что значительно снижает нагрузку на CPU сервера. Каждый участник отправляет один поток на сервер, сервер пересылает его остальным участникам.

### COTURN для NAT traversal

COTURN v4.6 запускается в Docker-контейнере с `network_mode: host` — это необходимо для корректной работы TURN, так как сервер должен быть доступен по реальным IP-адресам и портам. Конфигурация монтируется из `turnserver.conf`. TURN обеспечивает связь между клиентами, находящимися за NAT или симметричными файрволами, что критично для мобильных сетей.

### Медиа-стек Pion

Полный стек зависимостей из go.mod:
- `pion/ice/v4` — ICE-агент для установки соединений
- `pion/dtls/v3` — DTLS для шифрования сигнализации
- `pion/srtp/v3` — SRTP для шифрования медиа
- `pion/interceptor` — middleware для RTP/RTCP обработки
- `pion/sdp/v3` — парсинг и генерация SDP-описаний
- `pion/datachannel` — DataChannel для передачи данных
- `pion/stun/v3`, `pion/turn/v4` — STUN/TURN клиенты
- `pion/mdns/v2` — mDNS для локального обнаружения

### Шифрование

WebRTC обеспечивает обязательное шифрование медиа через DTLS + SRTP. Это отдельный слой от E2EE сообщений. E2EE для звонков потребует дополнительной реализации поверх стандартного WebRTC шифрования (insertable streams или SFrame).

## See Also

- [[entities/pulse-messenger]]
- [[concepts/flutter-go-messenger-architecture]]
- [[concepts/messenger-docker-infrastructure]]
