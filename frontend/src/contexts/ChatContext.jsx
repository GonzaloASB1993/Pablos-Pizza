import { createContext, useContext, useState, useEffect } from 'react'
import { io } from 'socket.io-client'
import { chatService } from '../services/chatService'
import toast from 'react-hot-toast'

const ChatContext = createContext({})

export const useChat = () => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

export const ChatProvider = ({ children }) => {
  const [socket, setSocket] = useState(null)
  const [chatRoom, setChatRoom] = useState(null)
  const [messages, setMessages] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  // Initialize chat room
  const initializeChatRoom = async (clientName, clientEmail) => {
    try {
      const room = await chatService.createChatRoom(clientName, clientEmail)
      setChatRoom(room)
      
      // Connect to WebSocket
      const newSocket = io(`${import.meta.env.VITE_API_URL}/chat/ws/${room.id}`)
      
      newSocket.on('connect', () => {
        setIsConnected(true)
      })

      newSocket.on('disconnect', () => {
        setIsConnected(false)
      })

      newSocket.on('message', (data) => {
        if (data.type === 'message') {
          setMessages(prev => [...prev, data.message])
          
          // Add to unread count if chat is closed
          if (!isOpen) {
            setUnreadCount(prev => prev + 1)
            toast(`Nuevo mensaje: ${data.message.message.substring(0, 50)}...`, {
              icon: '💬',
              duration: 3000,
            })
          }
        }
      })

      newSocket.on('room_closed', (data) => {
        toast.error(data.message)
        closeChatRoom()
      })

      setSocket(newSocket)
      
      // Load existing messages
      const existingMessages = await chatService.getChatMessages(room.id)
      setMessages(existingMessages)
      
      return room
    } catch (error) {
      console.error('Error initializing chat room:', error)
      toast.error('Error al inicializar el chat')
      throw error
    }
  }

  // Send message
  const sendMessage = async (message, senderName) => {
    if (!socket || !chatRoom) return

    try {
      await chatService.sendMessage(chatRoom.id, message, senderName, false)
      
      // Reset unread count when user sends a message
      setUnreadCount(0)
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Error al enviar mensaje')
    }
  }

  // Open chat
  const openChat = () => {
    setIsOpen(true)
    setUnreadCount(0)
  }

  // Close chat
  const closeChat = () => {
    setIsOpen(false)
  }

  // Close chat room and disconnect
  const closeChatRoom = () => {
    if (socket) {
      socket.disconnect()
      setSocket(null)
    }
    setChatRoom(null)
    setMessages([])
    setIsConnected(false)
    setIsOpen(false)
    setUnreadCount(0)
  }

  // Check room status
  const checkRoomStatus = async () => {
    if (!chatRoom) return null
    
    try {
      return await chatService.getRoomStatus(chatRoom.id)
    } catch (error) {
      console.error('Error checking room status:', error)
      return null
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (socket) {
        socket.disconnect()
      }
    }
  }, [socket])

  const value = {
    chatRoom,
    messages,
    isConnected,
    isOpen,
    unreadCount,
    initializeChatRoom,
    sendMessage,
    openChat,
    closeChat,
    closeChatRoom,
    checkRoomStatus
  }

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}