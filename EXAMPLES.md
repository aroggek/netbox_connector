# NetBox Connector - Usage Examples

## 1. Обогащение алертов информацией о хостах

```spl
index=security sourcetype=firewall action=blocked
| netboxenrich field=dest_ip netbox_url="https://netbox.example.com" netbox_token="token"
| eval severity=case(
    netbox_device_role="production", "critical",
    netbox_device_role="staging", "medium",
    1=1, "low"
  )
| table _time src_ip dest_ip netbox_name netbox_site netbox_device_role severity
```

## 2. Получение информации о множестве хостов из алерта

```spl
index=alerts
| eval hosts=split(affected_hosts, ",")
| mvexpand hosts
| netboxenrich field=hosts netbox_url="https://netbox.example.com" netbox_token="token"
| stats values(netbox_name) as devices values(netbox_site) as sites by alert_id
```

## 3. Инвентаризация устройств из NetBox

```spl
| inputlookup netbox_devices
| stats count by site device_type device_role
| sort -count
```

## 4. Поиск устройств в определенном датацентре

```spl
| inputlookup netbox_devices
| search site="DC-Moscow"
| table name device_type status primary_ip rack
```

## 5. Мониторинг изменений в NetBox

```spl
index=netbox sourcetype=netbox:device
| sort - _time
| streamstats current=f last(status) as previous_status by name
| where status != previous_status
| table _time name status previous_status site
```

## 6. Корреляция сетевых инцидентов с топологией

```spl
index=network ERROR
| netboxenrich field=host netbox_url="https://netbox.example.com" netbox_token="token"
| stats count by netbox_site netbox_rack
| where count > 5
```

## 7. Lookup по IP адресу

```spl
index=main sourcetype=access_log
| lookup netbox_ip_addresses address as client_ip OUTPUT dns_name assigned_object
| table _time client_ip dns_name assigned_object
```

## 8. Список виртуальных машин по кластеру

```spl
| inputlookup netbox_virtual_machines
| search cluster="VMware-Prod-01"
| table name status vcpus memory disk primary_ip
```
