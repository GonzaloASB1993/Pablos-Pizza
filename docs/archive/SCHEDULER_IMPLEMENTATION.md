# 📅 Automated WhatsApp Reminder System - Implementation Complete

## ✅ Implementation Summary

The automated WhatsApp reminder system for overdue events has been successfully implemented. The system will automatically check for events that are more than 2 days past their event date and haven't been marked as completed, then send WhatsApp notifications to Juan Pablo.

---

## 🎯 System Flow

### Daily Automated Process (11:00 AM Chile Time)

1. **⏰ Cloud Scheduler Trigger**
   - Runs every day at 11:00 AM (America/Santiago timezone)
   - Sends POST request to `/api/scheduler/check-overdue-events`

2. **🔍 Verification Query**
   - Queries Firestore `bookings` collection
   - Filters: `event_date < today - 2 days` AND `status != 'completed'`
   - Returns up to 50 overdue bookings

3. **🚫 Duplicate Prevention**
   - Checks `notifications` collection for recent reminders
   - Skips events that received a reminder in the last 3 days

4. **📱 WhatsApp Notification**
   - **1 overdue event**: Single reminder template (HXd00b109affda30cc4b0b2888b469014d)
   - **Multiple events**: Batch reminder template (HXd65d75d0e47eb7b489b112b2f18f3382)
   - **Recipient**: Juan Pablo (+56989424566)

5. **📊 Logging**
   - All notifications logged in `notifications` Firestore collection
   - Tracks: booking_id, template_sid, success status, timestamp

---

## 📦 Files Created/Modified

### New Files Created:

1. **`services/notification_service.py`** ✨
   - Notification tracking and logging
   - Duplicate prevention checks
   - Notification history queries
   - Daily limit enforcement

2. **`services/scheduler_service.py`** ✨
   - Main overdue detection logic
   - Query bookings past threshold
   - Filter and prepare notifications
   - Rate limiting (max 10/day)

3. **`scheduler.yaml`** ✨
   - Cloud Scheduler configuration
   - Deployment commands
   - Monitoring instructions
   - Testing guidelines

4. **`SCHEDULER_IMPLEMENTATION.md`** ✨
   - This documentation file

### Modified Files:

1. **`services/whatsapp_service.py`** 🔧
   - Added template SIDs for overdue reminders
   - `prepare_single_overdue_reminder_variables()`
   - `prepare_multiple_overdue_reminder_variables()`
   - `send_overdue_reminder()` - Main sending function

2. **`main.py`** 🔧
   - New endpoint: `/api/scheduler/check-overdue-events`
   - Supports both GET (manual test) and POST (scheduler)
   - Optional authentication token verification

3. **`.env`** 🔧
   - Added overdue reminder template SIDs
   - Scheduler configuration variables
   - Admin name configuration

---

## 🔧 Configuration Variables

### Environment Variables (.env)

```bash
# Admin Configuration
ADMIN_WHATSAPP_NUMBER=+56989424566
ADMIN_NAME=Juan Pablo

# Template SIDs
TEMPLATE_EVENT_OVERDUE_SINGLE_SID=HXd00b109affda30cc4b0b2888b469014d
TEMPLATE_EVENT_OVERDUE_MULTIPLE_SID=HXd65d75d0e47eb7b489b112b2f18f3382

# Scheduler Settings
OVERDUE_DAYS_THRESHOLD=2           # Days after event to consider overdue
MAX_REMINDERS_PER_DAY=10           # Rate limit
SCHEDULER_AUTH_TOKEN=your_token    # Optional security token
```

---

## 🚀 Deployment Steps

### 1. Deploy Backend Code

```bash
# From backend directory
cd backend

# Deploy to Cloud Run (Firebase will handle this)
firebase deploy --only functions
```

### 2. Set Up Cloud Scheduler

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set project
gcloud config set project pablospizza-d84bf

# Create scheduler job
gcloud scheduler jobs create http check-overdue-events \
  --schedule="0 11 * * *" \
  --time-zone="America/Santiago" \
  --uri="https://main-4kqeqojbsq-uc.a.run.app/api/scheduler/check-overdue-events" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --headers="X-CloudScheduler-JobName=check-overdue-events" \
  --attempt-deadline=300s \
  --max-retry-attempts=3 \
  --description="Check for overdue events and send WhatsApp reminders"
```

### 3. Verify Configuration

```bash
# List scheduler jobs
gcloud scheduler jobs list

# View job details
gcloud scheduler jobs describe check-overdue-events
```

---

## 🧪 Testing

### Manual Testing (Development)

#### Option 1: Direct GET Request
```bash
# Test without sending messages (dry run)
curl "http://localhost:5000/api/scheduler/check-overdue-events"

# Test with force flag (bypass rate limits)
curl "http://localhost:5000/api/scheduler/check-overdue-events?force=true"
```

#### Option 2: Using Browser
```
http://localhost:5000/api/scheduler/check-overdue-events?force=true
```

#### Option 3: Production Test
```bash
# Manually trigger Cloud Scheduler job
gcloud scheduler jobs run check-overdue-events

# View execution logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit 50
```

### Expected Response

```json
{
  "success": true,
  "message": "Check completed. Sent 1 reminder(s)",
  "overdue_count": 3,
  "pending_reminders": 1,
  "reminders_sent": 1,
  "threshold_date": "2025-10-11",
  "admin_notified": "+56989424566"
}
```

---

## 📱 WhatsApp Template Messages

### Single Event Reminder (Template 1)

```
Hola Juan Pablo! 👋

Recordatorio: El siguiente evento necesita ser completado:

🎉 Evento: María González - Pizzeros en Acción
📆 Fecha: 10/10/2025 (hace 3 días)
⚠️ Estado: Pendiente de completar

Por favor completa el evento:
🔗 https://pablospizza.web.app/admin/agendamientos

Esto ayuda a mantener registros precisos y control de costos. 💰📊

¡Gracias!
```

### Multiple Events Reminder (Template 2)

```
Hola Juan Pablo! 👋

Tienes 3 eventos pendientes de completar:

1. María González - Pizzeros en Acción (10/10/2025)
2. Pedro Sánchez - Pizza Party (09/10/2025)
3. Ana López - Pizza Party + Pizzeros en Acción (08/10/2025)

Por favor revisa y completa los eventos:
🔗 https://pablospizza.web.app/admin/agendamientos

Esto ayuda a mantener registros precisos y control de costos. 💰📊

¡Gracias!
```

---

## 📊 Database Structure

### New Firestore Collection: `notifications`

```javascript
{
  "id": "auto-generated-id",
  "booking_id": "booking-uuid",
  "booking_ids": ["uuid1", "uuid2"],  // For batch notifications
  "booking_count": 3,                  // For batch notifications
  "notification_type": "overdue_reminder_single" | "overdue_reminder_multiple",
  "recipient": "+56989424566",
  "template_sid": "HXd00b109affda30cc4b0b2888b469014d",
  "success": true,
  "error_message": null,
  "created_at": Timestamp,
  "sent_at": Timestamp
}
```

---

## 🔍 Monitoring & Logs

### View Scheduler Logs

```bash
# Cloud Scheduler execution logs
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=check-overdue-events" --limit 50

# Cloud Run application logs
gcloud logging read "resource.type=cloud_run_revision AND textPayload:overdue" --limit 50

# View in Console
# https://console.cloud.google.com/cloudscheduler?project=pablospizza-d84bf
```

### Check Notification History

Query Firestore `notifications` collection:
- Filter by `notification_type: overdue_reminder_single`
- Order by `created_at` descending
- View success/failure rates

---

## 🛡️ Security Features

1. **Rate Limiting**: Max 10 reminders per day
2. **Duplicate Prevention**: No reminders within 3 days for same event
3. **Optional Auth Token**: Verify `X-CloudScheduler-JobName` header
4. **Fail-Safe Queries**: Limits to 50 bookings per check
5. **Error Logging**: All failures logged to Firestore

---

## 💰 Cost Estimation

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Scheduler | 1 job × 30 days/month | $0.00 (free tier) |
| WhatsApp Messages | ~30 messages/month | ~$0.15/month |
| Firestore Reads | ~1,000 reads/month | $0.00 (free tier) |
| Firestore Writes | ~30 writes/month | $0.00 (free tier) |
| **Total** | | **~$0.15/month** |

---

## 🚨 Troubleshooting

### Issue: No reminders being sent

**Check:**
1. Cloud Scheduler job is active: `gcloud scheduler jobs describe check-overdue-events`
2. Cloud Run service is running
3. Environment variables are set correctly
4. Twilio credentials are valid
5. Check logs for errors

### Issue: Duplicate reminders

**Check:**
1. Notification tracking is working
2. `notifications` collection exists
3. No duplicate scheduler jobs running

### Issue: Wrong timezone

**Check:**
1. Scheduler timezone: `America/Santiago`
2. TIMEZONE env variable matches
3. Cloud Run region settings

---

## 📋 Useful Commands

### Scheduler Management

```bash
# Pause scheduler
gcloud scheduler jobs pause check-overdue-events

# Resume scheduler
gcloud scheduler jobs resume check-overdue-events

# Update schedule time (e.g., change to 10 AM)
gcloud scheduler jobs update http check-overdue-events --schedule="0 10 * * *"

# Delete job
gcloud scheduler jobs delete check-overdue-events
```

### Testing & Debugging

```bash
# Manual trigger
gcloud scheduler jobs run check-overdue-events

# View recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit 20 --format=json

# Stream live logs
gcloud logging tail "resource.type=cloud_run_revision"
```

---

## 🎯 Success Criteria

✅ **Completed Features:**
- [x] Daily automated check at 11:00 AM
- [x] Query events > 2 days overdue
- [x] Filter out completed events
- [x] Send single/batch WhatsApp reminders
- [x] Notification tracking and logging
- [x] Duplicate prevention (3-day window)
- [x] Rate limiting (10/day max)
- [x] Manual testing endpoint
- [x] Comprehensive error handling
- [x] Cloud Scheduler configuration

---

## 📞 Support

For issues or questions:
1. Check logs in Google Cloud Console
2. Review Firestore `notifications` collection
3. Test manually: `GET /api/scheduler/check-overdue-events?force=true`
4. Verify environment variables in `.env`

---

## 🔄 Next Steps (Optional Enhancements)

1. **Admin Dashboard Panel**
   - View notification history
   - Configure reminder settings
   - Pause/resume notifications
   - Set custom reminder intervals

2. **Advanced Features**
   - Multiple reminder intervals (2 days, 5 days, 7 days)
   - Reply via WhatsApp to mark complete
   - Weekly summary report
   - Notification preferences per admin

3. **Analytics**
   - Track completion rates after reminders
   - Measure average time to complete
   - Identify patterns in overdue events

---

**Implementation Date:** October 13, 2025
**Status:** ✅ Production Ready
**Last Updated:** October 13, 2025
