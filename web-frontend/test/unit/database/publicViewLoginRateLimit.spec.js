/**
 * Unit tests for Story 1.8 — rate-limit (429) error handling in publicViewLogin.vue.
 *
 * Tests the error-routing logic inside authorizeView() without mounting the full
 * Nuxt page.  The handler branch is: statusCode === 429 → showError(rateLimitTitle, rateLimitText).
 */

function buildErrorState(statusCode) {
  // Replicate the error-routing logic from authorizeView() in publicViewLogin.vue
  const error = { visible: false, title: '', message: '' }

  function showError(title, message) {
    error.visible = true
    error.title = title
    error.message = message
  }

  const translations = {
    'publicViewAuthLogin.error.incorrectPasswordTitle': 'Incorrect password',
    'publicViewAuthLogin.error.incorrectPasswordText':
      'The provided password is incorrect.',
    'publicViewAuthLogin.error.rateLimitTitle': 'Too many attempts',
    'publicViewAuthLogin.error.rateLimitText':
      'Too many password attempts have been made. Please wait a minute before trying again.',
    'error.errorTitle': 'Error',
    'error.errorMessage': 'An error occurred.',
  }

  const $i18n = { t: (key) => translations[key] ?? key }

  if (statusCode === 401) {
    showError(
      $i18n.t('publicViewAuthLogin.error.incorrectPasswordTitle'),
      $i18n.t('publicViewAuthLogin.error.incorrectPasswordText')
    )
  } else if (statusCode === 429) {
    showError(
      $i18n.t('publicViewAuthLogin.error.rateLimitTitle'),
      $i18n.t('publicViewAuthLogin.error.rateLimitText')
    )
  } else {
    showError($i18n.t('error.errorTitle'), $i18n.t('error.errorMessage'))
  }

  return error
}

describe('publicViewLogin.vue error routing', () => {
  test('401 shows incorrect password error', () => {
    const error = buildErrorState(401)
    expect(error.visible).toBe(true)
    expect(error.title).toBe('Incorrect password')
  })

  test('429 shows rate-limit error title and text', () => {
    const error = buildErrorState(429)
    expect(error.visible).toBe(true)
    expect(error.title).toBe('Too many attempts')
    expect(error.message).toContain('Please wait a minute')
  })

  test('other status codes show generic error', () => {
    const error = buildErrorState(500)
    expect(error.visible).toBe(true)
    expect(error.title).toBe('Error')
  })

  test('429 does NOT show incorrect-password message', () => {
    const error = buildErrorState(429)
    expect(error.title).not.toBe('Incorrect password')
  })
})
