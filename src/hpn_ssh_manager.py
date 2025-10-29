#!/usr/bin/env python3
"""
HPN SSH Manager для высокопроизводительного подключения сетевых дисков
Автор: KomarovAI
"""

import subprocess
import os
import logging
import time
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

class HPNSSHManager:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mount_points = {}
        self.ssh_config_path = "/app/configs/hpn_ssh_config"
        
    def setup_ssh_config(self) -> bool:
        """
        Создание оптимизированной SSH конфигурации для HPN SSH
        """
        try:
            ssh_config = f"""
# HPN SSH Configuration для максимальной производительности
Host hpn-storage
    HostName {self.config.get('HPN_REMOTE_HOST', '192.168.1.100')}
    User {self.config.get('HPN_REMOTE_USER', 'user')}
    Port {self.config.get('HPN_REMOTE_PORT', '2222')}
    IdentityFile /app/configs/hpn_key
    
    # HPN SSH специфичные оптимизации
    TCPRcvBufPoll yes
    HPNDisabled no
    HPNBufferSize 8MB
    
    # Производительные настройки
    Compression no
    Ciphers aes128-ctr,aes192-ctr,aes256-ctr
    MACs hmac-sha2-256,hmac-sha2-512
    
    # Соединение keep-alive
    ServerAliveInterval 60
    ServerAliveCountMax 3
    
    # Мультиплексирование соединений
    ControlMaster auto
    ControlPath /tmp/ssh_mux_%h_%p_%r
    ControlPersist 10m
    
    # Быстрое подключение
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    
    # Отключение X11 forwarding для производительности
    ForwardX11 no
    ForwardAgent no
            """
            
            Path(self.ssh_config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.ssh_config_path, 'w') as f:
                f.write(ssh_config)
                
            os.chmod(self.ssh_config_path, 0o600)
            self.logger.info("SSH конфигурация создана успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка создания SSH конфигурации: {e}")
            return False
    
    def mount_hpn_storage(self, remote_path: str, local_mount_point: str, 
                         ssh_config_name: str = "hpn-storage") -> bool:
        """
        Монтирование удаленного хранилища через оптимизированный HPN SSH + SSHFS
        """
        try:
            # Создание точки монтирования
            Path(local_mount_point).mkdir(parents=True, exist_ok=True)
            
            # Проверка, не смонтирован ли уже
            if self.is_mounted(local_mount_point):
                self.logger.info(f"Путь {local_mount_point} уже смонтирован")
                return True
            
            # Максимально оптимизированная команда SSHFS с HPN SSH
            sshfs_cmd = [
                'sshfs',
                f'{ssh_config_name}:{remote_path}',
                local_mount_point,
                
                # Использование нашей SSH конфигурации
                '-F', self.ssh_config_path,
                
                # Кэширование для максимальной производительности  
                '-o', 'cache=yes',
                '-o', 'kernel_cache',
                '-o', 'cache_timeout=115',
                
                # Оптимизации SSHFS
                '-o', 'direct_io',              # Прямой I/O
                '-o', 'large_read',             # Большие блоки чтения
                '-o', 'max_read=65536',         # Максимальный размер чтения
                '-o', 'max_conns=10',           # Множественные соединения
                '-o', 'big_writes',             # Большие блоки записи
                
                # Производительные настройки
                '-o', 'Compression=no',         # Отключаем сжатие
                '-o', 'Cipher=aes128-ctr',      # Быстрый шифр
                
                # Надежность и переподключение
                '-o', 'reconnect',
                '-o', 'ServerAliveInterval=15',
                '-o', 'ServerAliveCountMax=3',
                
                # Права доступа
                '-o', 'allow_other',
                '-o', 'default_permissions',
                
                # Отключение проверок для производительности
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null'
            ]
            
            self.logger.info(f"Монтируем HPN SSH хранилище: {remote_path} -> {local_mount_point}")
            
            # Запуск команды монтирования
            result = subprocess.run(sshfs_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.mount_points[local_mount_point] = {
                    'remote_path': remote_path,
                    'ssh_config': ssh_config_name,
                    'status': 'mounted',
                    'mount_time': time.time()
                }
                self.logger.info(f"Успешно смонтировано HPN SSH хранилище: {local_mount_point}")
                return True
            else:
                self.logger.error(f"Ошибка монтирования HPN SSH: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Исключение при монтировании HPN SSH: {e}")
            return False
    
    def is_mounted(self, mount_point: str) -> bool:
        """
        Проверка, смонтирован ли путь
        """
        try:
            result = subprocess.run(['mount'], capture_output=True, text=True)
            return mount_point in result.stdout
        except Exception:
            return False
    
    def unmount_hpn_storage(self, mount_point: str) -> bool:
        """
        Размонтирование HPN SSH хранилища
        """
        try:
            if not self.is_mounted(mount_point):
                self.logger.info(f"Путь {mount_point} не смонтирован")
                return True
                
            result = subprocess.run(['fusermount3', '-u', mount_point], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                if mount_point in self.mount_points:
                    del self.mount_points[mount_point]
                self.logger.info(f"Успешно размонтировано: {mount_point}")
                return True
            else:
                self.logger.error(f"Ошибка размонтирования: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Исключение при размонтировании: {e}")
            return False
    
    def check_mount_health(self, mount_point: str) -> bool:
        """
        Проверка состояния HPN SSH монтирования
        """
        try:
            if not self.is_mounted(mount_point):
                return False
                
            # Простая проверка доступности через ls
            result = subprocess.run(['ls', mount_point], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def benchmark_performance(self, mount_point: str) -> Dict:
        """
        Бенчмарк производительности HPN SSH хранилища
        """
        try:
            benchmark_file = os.path.join(mount_point, 'hpn_benchmark.tmp')
            
            # Тест записи (100MB)
            write_cmd = [
                'dd', 'if=/dev/zero', f'of={benchmark_file}',
                'bs=1M', 'count=100', 'conv=fdatasync'
            ]
            
            self.logger.info("Запуск теста записи...")
            start_time = time.time()
            result = subprocess.run(write_cmd, capture_output=True, text=True)
            write_time = time.time() - start_time
            
            if result.returncode != 0:
                return {'status': 'failed', 'error': 'write test failed'}
            
            write_speed = 100 / write_time  # MB/s
            
            # Тест чтения
            read_cmd = [
                'dd', f'if={benchmark_file}', 'of=/dev/null',
                'bs=1M', 'count=100'
            ]
            
            self.logger.info("Запуск теста чтения...")
            start_time = time.time()
            result = subprocess.run(read_cmd, capture_output=True, text=True)
            read_time = time.time() - start_time
            
            # Очистка
            try:
                os.unlink(benchmark_file)
            except:
                pass
            
            if result.returncode != 0:
                return {'status': 'failed', 'error': 'read test failed'}
                
            read_speed = 100 / read_time
            
            benchmark_result = {
                'write_speed_mbps': round(write_speed, 2),
                'read_speed_mbps': round(read_speed, 2),
                'write_time_sec': round(write_time, 2),
                'read_time_sec': round(read_time, 2),
                'status': 'success'
            }
            
            self.logger.info(f"Benchmark результаты: {benchmark_result}")
            return benchmark_result
                    
        except Exception as e:
            self.logger.error(f"Benchmark не удался: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def get_connection_status(self) -> Dict:
        """
        Получение статуса всех HPN SSH подключений
        """
        status = {
            'total_mounts': len(self.mount_points),
            'active_mounts': 0,
            'failed_mounts': 0,
            'mounts': {}
        }
        
        for mount_point, info in self.mount_points.items():
            is_healthy = self.check_mount_health(mount_point)
            
            if is_healthy:
                status['active_mounts'] += 1
                mount_status = 'active'
            else:
                status['failed_mounts'] += 1
                mount_status = 'failed'
                
            status['mounts'][mount_point] = {
                'remote_path': info['remote_path'],
                'status': mount_status,
                'mount_time': info.get('mount_time', 0),
                'uptime_hours': round((time.time() - info.get('mount_time', time.time())) / 3600, 2)
            }
            
        return status
    
    def generate_pc_setup_script(self) -> str:
        """
        Генерация скрипта установки HPN SSH сервера на компьютере
        """
        setup_script = f"""
#!/bin/bash
# Скрипт установки HPN SSH сервера для file-pull проекта
# Автоматически сгенерирован HPNSSHManager

echo "🚀 Установка HPN SSH сервера..."

# Обновление системы
sudo apt update

# Установка зависимостей
sudo apt install -y build-essential git cmake wget

# Скачивание и компиляция HPN SSH
cd /tmp
wget https://github.com/rapier1/hpn-ssh/archive/master.zip
unzip master.zip
cd hpn-ssh-master

# Конфигурация и компиляция
./configure --prefix=/usr/local --with-ssl-dir=/usr/lib/ssl
make
sudo make install

# Создание конфигурации HPN SSH сервера
sudo tee /usr/local/etc/sshd_config << EOF
Port {self.config.get('HPN_REMOTE_PORT', '2222')}
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
TCPRcvBufPoll yes
HPNDisabled no
HPNBufferSize 8MB
AllowUsers {self.config.get('HPN_REMOTE_USER', 'user')}
EOF

# Создание systemd сервиса
sudo tee /etc/systemd/system/hpnsshd.service << EOF
[Unit]
Description=HPN SSH Daemon
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/sbin/sshd -f /usr/local/etc/sshd_config
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
Restart=on-failure
RestartSec=42s

[Install]
WantedBy=multi-user.target
EOF

# Сетевые оптимизации
sudo sysctl -w net.core.rmem_max=67108864
sudo sysctl -w net.core.wmem_max=67108864
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr

# Постоянные настройки
echo "net.core.rmem_max = 67108864" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 67108864" | sudo tee -a /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control = bbr" | sudo tee -a /etc/sysctl.conf

# Запуск сервиса
sudo systemctl daemon-reload
sudo systemctl enable hpnsshd
sudo systemctl start hpnsshd

echo "✅ Установка HPN SSH сервера завершена!"
echo "📋 Не забудьте:"
echo "   1. Добавить публичный ключ в ~/.ssh/authorized_keys"
echo "   2. Настроить брандмауэр для порта {self.config.get('HPN_REMOTE_PORT', '2222')}"
echo "   3. Проверить статус: systemctl status hpnsshd"
        """
        
        return setup_script