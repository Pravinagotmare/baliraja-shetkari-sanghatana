# WhatsApp Cloud API Setup

The Admin panel sends one common message using an approved WhatsApp message template. The template must have exactly one text placeholder (`{{1}}`) in its body. The text entered in the app fills that placeholder.

## Meta configuration

1. Set up a WhatsApp Business Platform Cloud API phone number and a Meta app for the organization.
2. Create and get approval for a template in the required language. Include one body text variable (`{{1}}`). Copy its exact template name and language code.
3. Create a production access token with the `whatsapp_business_messaging` permission and copy the phone number ID for the registered sender.
4. On the app server, place the values below in its private `.env` file. Never commit this file or paste the access token into the app UI or chat.

```dotenv
WHATSAPP_ACCESS_TOKEN=your-long-lived-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id
WHATSAPP_API_VERSION=vXX.X
WHATSAPP_TEMPLATE_NAME=your_approved_template_name
WHATSAPP_TEMPLATE_LANGUAGE=mr
```

Replace `vXX.X` with a currently supported Graph API version from Meta's app/API settings. Restart Streamlit after changing server environment settings.

## Sending

Only active members with WhatsApp consent recorded are eligible. Record consent only after the member has explicitly agreed to receive WhatsApp messages. The Admin panel previews recipient count and numbers, lets the operator choose recipients, and requires a confirmation before making one API call per recipient. Invalid Indian mobile numbers are skipped and shown for correction. Attempts and provider message IDs are stored in `whatsapp_message_logs`.

An accepted API request is not proof that the message reached the recipient's phone. Delivery and read status require a configured WhatsApp webhook, which this integration does not yet include.

Meta API reference: https://www.postman.com/meta/whatsapp-business-platform/folder/o48mro7/messages
