# p2pswapbot
# P2P Bitcoin Swap Bot - Descripción Completa del Proyecto

## Concepto Central

Bot de Telegram que facilita intercambios peer-to-peer entre Lightning Network y Bitcoin onchain sin custodia de fondos. Los usuarios pueden crear ofertas para intercambiar sats de Lightning por Bitcoin onchain (swap out) o Bitcoin onchain por Lightning sats (swap in).

## Motivación del Proyecto

El proyecto surgió como alternativa a servicios como Lightning Loop, que requiere montos mínimos altos (250k sats) y depende de servicios centralizados. La idea era crear un marketplace P2P descentralizado donde usuarios con diferentes necesidades de liquidez pudieran intercambiar directamente.

## Arquitectura Técnica

**Stack Tecnológico:**
- Backend: Python 3.9
- Framework Bot: python-telegram-bot 21.3
- Base de Datos: SQLite + SQLAlchemy
- Red Bitcoin: Testnet (preparación para mainnet)
- Configuración: python-dotenv

**Estructura del Proyecto:**
```
p2pswapbot/
├── src/
│   ├── bot.py              # Bot principal
│   └── database/
│       └── models.py       # Modelos User, Offer, Deal
├── requirements.txt
├── setup_database.py
└── .env
```

## Evolución del Desarrollo

### Sprint 1 - Infraestructura Base (Completado)
**Objetivo:** Bot básico funcionando con persistencia

**Logros:**
- Bot de Telegram operativo con comandos básicos (/start, /help, /perfil)
- Base de datos SQLite con 3 modelos (User, Offer, Deal)
- Sistema de usuarios con registro automático
- Logging y manejo básico de errores
- Configuración de entorno con variables seguras

**Tecnología implementada:**
- python-telegram-bot para interfaz Telegram
- SQLAlchemy para ORM y persistencia
- Sistema de logging para debugging

### Sprint 2 - Sistema de Ofertas (Completado)
**Objetivo:** Usuarios pueden crear y gestionar ofertas

**Logros:**
- Comandos /vender y /comprar (posteriormente migrados a /swapout y /swapin)
- Validación de montos estándar (10k, 50k, 100k, 500k, 1M sats)
- Base de datos de ofertas con estados (active, taken, completed)
- Comando /ofertas para visualizar marketplace
- Sistema básico de deals al tomar ofertas

**Decisiones de diseño:**
- Montos estandarizados para mejorar privacidad y liquidez
- Estados de ofertas para tracking del lifecycle
- Separación clara entre ofertas y deals ejecutándose

### Sprint 3 - Transformación UX (En progreso)
**Objetivo:** Interface profesional en inglés con canal público

**Cambios implementados:**
- Migración completa de español a inglés
- Terminología técnica precisa: swap out (Lightning→Bitcoin) y swap in (Bitcoin→Lightning)
- Sistema de botones inline en lugar de comandos de texto
- Canal público @btcp2pswapoffers para distribución de ofertas
- Auto-publicación de ofertas en canal al crearlas

**Mejoras de UX:**
- Interfaz con botones [10k] [50k] [100k] [500k] [1M] para selección de montos
- Mensajes concisos y claros
- Terminología universalmente entendible en crypto
- Visibilidad pública de ofertas para aumentar liquidez

## Estado Actual del Sistema

### Funcionalidades Operativas:
1. **Registro de usuarios** - Automático al usar /start
2. **Creación de ofertas** - Swap out y swap in con botones
3. **Marketplace público** - Canal de Telegram para visibilidad
4. **Tomar ofertas** - Sistema básico de matching
5. **Tracking de deals** - Base de datos de intercambios activos

### Flujos de Usuario Actuales:

**Crear Swap Out (Lightning → Bitcoin):**
1. /swapout → Botones de monto → Oferta creada → Publicada en canal

**Crear Swap In (Bitcoin → Lightning):**
1. /swapin → Botones de monto → Oferta creada → Publicada en canal

**Tomar Oferta:**
1. /take [ID] → Deal creado → Notificación a ambas partes

## Gaps Técnicos Identificados

### Inmediatos (Sprint 3 continuación):
1. **Post-match workflow**: Capturar dirección Bitcoin después de tomar swap out
2. **Lightning invoice handling**: Solicitar invoices para swap in
3. **Sistema de escrow básico**: Multisig 2-of-3 en testnet
4. **Monitoreo de transacciones**: Detección automática de depósitos

### Medianos (Sprint 4):
1. **Estados de conversación**: Tracking de usuarios en procesos multi-paso
2. **Validaciones robustas**: Direcciones Bitcoin, Lightning invoices
3. **Manejo de timeouts**: Expiración de deals inactivos
4. **Sistema de disputas**: Resolución de conflictos

### Avanzados (Futuros sprints):
1. **Escrow automático**: Release basado en confirmaciones blockchain
2. **Sistema de reputación**: Scoring basado en historial
3. **Características de privacidad**: Mixing de transacciones, timing aleatorio
4. **Integración Lightning**: HODL invoices, submarine swaps nativos

## Decisiones de Diseño Clave

**Privacidad:**
- Montos estandarizados para evitar fingerprinting
- Usernames ocultos en ofertas públicas (solo calificación numérica)
- Direcciones Bitcoin solicitadas just-in-time

**Seguridad:**
- Sin custodia de fondos por el bot
- Multisig 2-of-3 para escrow (comprador + vendedor + bot para arbitraje)
- Validaciones exhaustivas en cada paso

**UX:**
- Interfaz simple con botones
- Terminología clara y universal
- Canal público para discovery
- Procesos step-by-step guiados

## Desafíos Técnicos Resueltos

1. **Gestión de base de datos**: SQLAlchemy ORM con manejo correcto de sesiones
2. **Estados de objetos**: Prevención de DetachedInstanceError en operaciones async
3. **Integración de canal**: Auto-posting de ofertas con manejo de errores
4. **Interfaz de botones**: CallbackQueryHandler para interacciones inline
5. **Versionado de dependencias**: Resolución de conflictos en python-telegram-bot

## Métricas y KPIs

**Técnicas:**
- Ofertas creadas por día
- Deals completados exitosamente
- Tiempo promedio de completar intercambio
- Tasa de error en transacciones

**De negocio:**
- Volumen total de sats intercambiados
- Usuarios activos únicos
- Retención de usuarios
- Crecimiento del marketplace

## Roadmap Técnico

**Próximos 30 días:**
- Completar flujo post-match para ambos tipos de swap
- Implementar escrow multisig básico en testnet
- Sistema de monitoreo de transacciones Bitcoin
- Manejo robusto de Lightning invoices

**60-90 días:**
- Sistema de disputas y arbitraje
- Release automático basado en confirmaciones
- Migración gradual a mainnet
- Optimizaciones de performance

El proyecto demuestra evolución de concepto MVP a plataforma de intercambio funcional, con enfoque en seguridad, privacidad y experiencia de usuario profesional.
