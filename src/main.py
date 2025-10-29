#!/usr/bin/env python3
"""
File-Pull с интеграцией HPN SSH для высокопроизводительного доступа к сетевым дискам
Автор: KomarovAI
"""

import os
import time
import subprocess
import sys
from loguru import logger
from hpn_ssh_manager import HPNSSHManager

# Настройки окружения
MERGER_MOUNT_POINT = os.environ.get("MERGER_MOUNT_POINT", "/data/unified")
HPN_REMOTE_MOUNT = "/mnt/hpn-remote"

# Пути для проверки
CHECK_PATHS = [MERGER_MOUNT_POINT, "/mnt/webdav", "/mnt/rclone", "/data/local", HPN_REMOTE_MOUNT]

# Настройка логирования
logger.add("/var/log/file-pull/app.log", rotation="10 MB")
logger.add("/var/log/file-pull/hpn_ssh.log", rotation="10 MB", filter=lambda record: "hpn" in record["name"].lower())


def load_hpn_config() -> dict:
    """
    Загрузка конфигурации HPN SSH из переменных окружения
    """
    return {
        'HPN_REMOTE_HOST': os.environ.get('HPN_REMOTE_HOST', ''),
        'HPN_REMOTE_USER': os.environ.get('HPN_REMOTE_USER', ''),
        'HPN_REMOTE_PORT': os.environ.get('HPN_REMOTE_PORT', '2222'),
        'HPN_REMOTE_PATH': os.environ.get('HPN_REMOTE_PATH', '/home'),
        'HPN_ENABLED': os.environ.get('HPN_ENABLED', 'false').lower() == 'true'
    }


def is_mounted(path: str) -> bool:
    """
    Проверка, смонтирован ли путь
    """
    try:
        out = subprocess.check_output(["mount"]).decode()
        return any(path in line for line in out.splitlines())
    except Exception:
        return False


def setup_hpn_ssh(hpn_manager: HPNSSHManager, config: dict) -> bool:
    """
    Настройка и монтирование HPN SSH хранилища
    """
    if not config.get('HPN_ENABLED'):
        logger.info("HPN SSH отключен в конфигурации")
        return True
        
    if not config.get('HPN_REMOTE_HOST'):
        logger.warning("HPN_REMOTE_HOST не задан, пропускаем HPN SSH")
        return True
    
    logger.info(f"🚀 Настройка HPN SSH подключения к {config['HPN_REMOTE_HOST']}")
    
    # Создание SSH конфигурации
    if not hpn_manager.setup_ssh_config():
        logger.error("Ошибка создания SSH конфигурации")
        return False
    
    # Монтирование HPN SSH хранилища
    success = hpn_manager.mount_hpn_storage(
        remote_path=config['HPN_REMOTE_PATH'],
        local_mount_point=HPN_REMOTE_MOUNT
    )
    
    if success:
        logger.success(f"✅ HPN SSH хранилище успешно смонтировано: {HPN_REMOTE_MOUNT}")
        
        # Запуск бенчмарка производительности
        logger.info("📊 Запуск теста производительности HPN SSH...")
        benchmark = hpn_manager.benchmark_performance(HPN_REMOTE_MOUNT)
        
        if benchmark.get('status') == 'success':
            logger.success(
                f"📈 Производительность HPN SSH: "
                f"Запись: {benchmark['write_speed_mbps']} МБ/с, "
                f"Чтение: {benchmark['read_speed_mbps']} МБ/с"
            )
        else:
            logger.warning(f"⚠️ Бенчмарк не удался: {benchmark.get('error', 'unknown')}")
            
        return True
    else:
        logger.error("❌ Не удалось смонтировать HPN SSH хранилище")
        return False


def ensure_mounts(hpn_manager: HPNSSHManager = None) -> bool:
    """
    Проверка и восстановление всех монтирований
    """
    ok = True
    mount_status = {}
    
    for p in CHECK_PATHS:
        if os.path.isdir(p):
            mounted = is_mounted(p)
            mount_status[p] = mounted
            logger.info(f"📁 {p} смонтирован={mounted}")
            
            # Особая обработка MergerFS
            if p == MERGER_MOUNT_POINT and not mounted:
                logger.warning("⚠️ MergerFS не смонтирован, пытаемся повторить setup.sh")
                subprocess.call(["/bin/bash", "-lc", "/app/scripts/setup.sh"]) 
                time.sleep(3)
                mounted = is_mounted(p)
                mount_status[p] = mounted
                if not mounted:
                    ok = False
                    
            # Особая обработка HPN SSH
            elif p == HPN_REMOTE_MOUNT and not mounted and hpn_manager:
                logger.warning("⚠️ HPN SSH не смонтирован, пытаемся переподключить")
                config = load_hpn_config()
                if config.get('HPN_ENABLED') and config.get('HPN_REMOTE_HOST'):
                    success = hpn_manager.mount_hpn_storage(
                        remote_path=config['HPN_REMOTE_PATH'],
                        local_mount_point=HPN_REMOTE_MOUNT
                    )
                    if not success:
                        ok = False
        else:
            logger.warning(f"⚠️ {p} отсутствует")
            mount_status[p] = False
    
    # Логирование общего статуса
    total_mounts = len(CHECK_PATHS)
    active_mounts = sum(1 for status in mount_status.values() if status)
    logger.info(f"📊 Статус монтирования: {active_mounts}/{total_mounts} активны")
    
    return ok


def log_system_info():
    """
    Логирование информации о системе при старте
    """
    try:
        # Информация о системе
        hostname = subprocess.check_output(['hostname']).decode().strip()
        uptime = subprocess.check_output(['uptime']).decode().strip()
        
        logger.info(f"🖥️ Система: {hostname}")
        logger.info(f"⏰ Uptime: {uptime}")
        
        # Проверка доступности HPN SSH
        try:
            hpn_version = subprocess.check_output(['/usr/local/bin/ssh', '-V'], stderr=subprocess.STDOUT).decode().strip()
            logger.info(f"🔐 HPN SSH: {hpn_version}")
        except:
            logger.warning("⚠️ HPN SSH не найден или не установлен")
            
        # Сетевые интерфейсы
        try:
            interfaces = subprocess.check_output(['ip', 'addr', 'show']).decode()
            active_interfaces = [line.strip() for line in interfaces.split('\n') if 'inet ' in line and '127.0.0.1' not in line]
            logger.info(f"🌐 Сетевые интерфейсы: {len(active_interfaces)} активных")
        except:
            pass
            
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить информацию о системе: {e}")


def main():
    """
    Основная функция приложения
    """
    logger.info("🚀 FILE-PULL с HPN SSH интеграцией стартует")
    
    # Логирование системной информации
    log_system_info()
    
    # Загрузка конфигурации HPN SSH
    hpn_config = load_hpn_config()
    logger.info(f"⚙️ HPN SSH статус: {'включен' if hpn_config.get('HPN_ENABLED') else 'отключен'}")
    
    # Инициализация HPN SSH Manager
    hpn_manager = None
    if hpn_config.get('HPN_ENABLED'):
        hpn_manager = HPNSSHManager(hpn_config)
        
        # Настройка HPN SSH при первом запуске
        if not setup_hpn_ssh(hpn_manager, hpn_config):
            logger.error("❌ Критическая ошибка настройки HPN SSH")
            # Продолжаем работу без HPN SSH
            hpn_manager = None
    
    # Основной цикл мониторинга
    check_interval = 15  # секунд
    health_check_counter = 0
    
    while True:
        try:
            # Проверка монтирований
            ok = ensure_mounts(hpn_manager)
            
            if not ok:
                logger.error("❌ Не удалось восстановить некоторые монтирования")
            
            # Расширенная проверка состояния каждые 5 циклов (75 секунд)
            health_check_counter += 1
            if health_check_counter >= 5:
                health_check_counter = 0
                
                if hpn_manager:
                    # Получение детального статуса HPN SSH
                    status = hpn_manager.get_connection_status()
                    logger.info(
                        f"📊 HPN SSH статус: {status['active_mounts']}/{status['total_mounts']} активны"
                    )
                    
                    # Проверка здоровья каждого HPN SSH монтирования
                    for mount_point, info in status['mounts'].items():
                        if info['status'] == 'failed':
                            logger.warning(
                                f"🔄 Попытка восстановления неисправного HPN SSH монтирования: {mount_point}"
                            )
                            # Попытка переподключения
                            hpn_manager.unmount_hpn_storage(mount_point)
                            time.sleep(2)
                            hpn_manager.mount_hpn_storage(
                                remote_path=hpn_config['HPN_REMOTE_PATH'],
                                local_mount_point=mount_point
                            )
            
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            logger.info("📝 Получен сигнал завершения")
            break
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка в главном цикле: {e}")
            time.sleep(check_interval)
    
    # Cleanup при завершении
    if hpn_manager:
        logger.info("🧹 Очистка HPN SSH подключений")
        for mount_point in list(hpn_manager.mount_points.keys()):
            hpn_manager.unmount_hpn_storage(mount_point)
    
    logger.info("👋 FILE-PULL завершает работу")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Завершение по запросу пользователя")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)