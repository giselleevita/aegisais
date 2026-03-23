import type { WebSocketMessage } from '@/shared/types/common'

export type AmlOutletContext = {
  lastMessage: WebSocketMessage | null
}
