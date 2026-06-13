import { describe, test, expect } from 'vitest'
import {
  RowCommentMentionNotificationType,
  RowCommentCreatedNotificationType,
} from '@baserow/modules/database/notificationTypes'
import RowCommentMentionNotification from '@baserow/modules/database/components/notifications/RowCommentMentionNotification'
import RowCommentCreatedNotification from '@baserow/modules/database/components/notifications/RowCommentCreatedNotification'
import NotificationSenderInitialsIcon from '@baserow/modules/core/components/notifications/NotificationSenderInitialsIcon'

describe('RowCommentMentionNotificationType', () => {
  test('getType returns row_comment_mention', () => {
    expect(RowCommentMentionNotificationType.getType()).toBe('row_comment_mention')
  })

  test('getContentComponent returns RowCommentMentionNotification', () => {
    const instance = new RowCommentMentionNotificationType({})
    expect(instance.getContentComponent()).toBe(RowCommentMentionNotification)
  })

  test('getIconComponent returns NotificationSenderInitialsIcon', () => {
    const instance = new RowCommentMentionNotificationType({})
    expect(instance.getIconComponent()).toBe(NotificationSenderInitialsIcon)
  })
})

describe('RowCommentCreatedNotificationType', () => {
  test('getType returns row_comment_created', () => {
    expect(RowCommentCreatedNotificationType.getType()).toBe('row_comment_created')
  })

  test('getContentComponent returns RowCommentCreatedNotification', () => {
    const instance = new RowCommentCreatedNotificationType({})
    expect(instance.getContentComponent()).toBe(RowCommentCreatedNotification)
  })

  test('getIconComponent returns NotificationSenderInitialsIcon', () => {
    const instance = new RowCommentCreatedNotificationType({})
    expect(instance.getIconComponent()).toBe(NotificationSenderInitialsIcon)
  })
})
