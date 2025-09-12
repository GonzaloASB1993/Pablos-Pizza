import { chatAPI } from './api'

export const chatService = {
  // Create new chat room
  createChatRoom: async (clientName, clientEmail) => {
    const response = await chatAPI.createRoom({ 
      client_name: clientName, 
      client_email: clientEmail 
    })
    return response.data
  },

  // Get chat rooms (for admin)
  getChatRooms: async (activeOnly = true) => {
    const response = await chatAPI.getRooms({ active_only: activeOnly })
    return response.data
  },

  // Get messages for a room
  getChatMessages: async (roomId, limit = 50) => {
    const response = await chatAPI.getMessages(roomId, { limit })
    return response.data
  },

  // Send message
  sendMessage: async (roomId, message, senderName, isAdmin = false) => {
    const response = await chatAPI.sendMessage(roomId, {
      message,
      sender_name: senderName,
      is_admin: isAdmin
    })
    return response.data
  },

  // Close chat room
  closeChatRoom: async (roomId) => {
    const response = await chatAPI.closeRoom(roomId)
    return response.data
  },

  // Get room status
  getRoomStatus: async (roomId) => {
    const response = await chatAPI.getRoomStatus(roomId)
    return response.data
  },

  // Format message for display
  formatMessage: (message) => {
    return {
      id: message.id,
      text: message.message,
      sender: message.sender_name,
      isAdmin: message.is_admin,
      timestamp: new Date(message.timestamp),
      time: new Date(message.timestamp).toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit'
      })
    }
  },

  // Check if admin is online
  isAdminOnline: async (roomId) => {
    try {
      const status = await chatService.getRoomStatus(roomId)
      return status.admin_online
    } catch (error) {
      console.error('Error checking admin status:', error)
      return false
    }
  }
}

export default chatService