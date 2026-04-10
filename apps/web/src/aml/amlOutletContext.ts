import type { AuthContextResponse, WebSocketMessage } from '@/shared/types/common'

export type AmlOutletContext = {
  lastMessage: WebSocketMessage | null
  authContext: AuthContextResponse | null
}
