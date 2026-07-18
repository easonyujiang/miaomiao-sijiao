import { type Page, type APIRequestContext, expect } from '@playwright/test'

export const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'
export const FRONTEND = process.env.FRONTEND_URL || 'http://localhost:3000'
export const SLUG = 'ashley'

/** 等待后端就绪 */
export async function waitForBackend(api: APIRequestContext) {
  await expect.poll(
    async () => {
      const res = await api.get(`${BACKEND}/health`)
      return res.ok()
    },
    { timeout: 20_000, intervals: [500, 1000, 2000] },
  ).toBeTruthy()
}

/** 等待前端就绪 */
export async function waitForFrontend(page: Page) {
  await page.goto('/')
  await expect(page.locator('h1')).toBeVisible({ timeout: 20_000 })
}

/** 打开妙喵聊天窗口 */
export async function openPetChat(page: Page) {
  const btn = page.locator('[data-pet-assistant]').first()
  await btn.click()
  await expect(page.locator('[data-pet-assistant]').nth(1)).toBeVisible()
}

/** 在聊天窗口发送消息并等待回复 */
export async function sendChatMessage(page: Page, message: string) {
  const input = page.locator('[data-pet-assistant] input[placeholder="Ask anything"]')
  const countBefore = await page.locator('[data-pet-assistant] .max-w-\\[88\\%\\]').count()
  await input.fill(message)
  await input.press('Enter')
  // 等待新消息出现（pending 状态结束）
  await expect(page.locator('[data-pet-assistant] .max-w-\\[88\\%\\]')).toHaveCount(countBefore + 1, { timeout: 30_000 })
}

/** 获取聊天窗口中所有消息文本 */
export async function getChatMessages(page: Page): Promise<string[]> {
  const messages = page.locator('[data-pet-assistant] .max-w-\\[88\\%\\] p')
  return messages.allTextContents()
}
