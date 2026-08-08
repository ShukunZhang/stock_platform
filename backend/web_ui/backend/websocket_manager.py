"""
WebSocket Manager for handling real-time communication with frontend clients.
Provides connection management, message broadcasting, and real-time status updates.
"""

import json
import uuid
import logging
from typing import Dict, Set, Any, Optional, List, Callable
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta
import asyncio
from enum import Enum
from dataclasses import dataclass, asdict
import traceback

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    CONNECTION_ESTABLISHED = "connection_established"
    PING = "ping"
    PONG = "pong"
    STATUS_UPDATE = "status_update"
    AGENT_RESPONSE = "agent_response"
    AGENT_STATUS = "agent_status"
    AGENT_STEP = "agent_step"
    TOOL_CALL = "tool_call"
    QUERY_ANALYSIS = "query_analysis"
    FINAL_RECOMMENDATION = "final_recommendation"
    QUERY_STARTED = "query_started"
    QUERY_COMPLETED = "query_completed"
    PORTFOLIO_UPDATE = "portfolio_update"
    ERROR = "error"
    SYSTEM_NOTIFICATION = "system_notification"


@dataclass
class WebSocketMessage:
    """Structured WebSocket message."""
    type: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    client_id: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    client_id: str
    connected_at: datetime
    last_activity: datetime
    message_count: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "client_id": self.client_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": self.message_count,
            "connection_duration": str(datetime.now() - self.connected_at),
            "user_agent": self.user_agent,
            "ip_address": self.ip_address
        }


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting with advanced features.
    
    Features:
    - Connection lifecycle management
    - Message broadcasting and targeted messaging
    - Real-time status updates during agent processing
    - Message serialization and error handling
    - Connection health monitoring
    - Message queuing and retry logic
    """
    
    def __init__(self, max_connections: int = 100, ping_interval: int = 30):
        # Store active connections with client IDs
        self.active_connections: Dict[str, WebSocket] = {}
        # Track connection metadata
        self.connection_info: Dict[str, ConnectionInfo] = {}
        # Message handlers for different message types
        self.message_handlers: Dict[str, Callable] = {}
        # Configuration
        self.max_connections = max_connections
        self.ping_interval = ping_interval
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        # Message queue for failed deliveries
        self._message_queue: Dict[str, List[WebSocketMessage]] = {}
        # Statistics
        self._stats = {
            "total_connections": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "broadcasts_sent": 0
        }
        
    async def connect(self, websocket: WebSocket, user_agent: str = None, ip_address: str = None) -> str:
        """
        Accept a new WebSocket connection and assign a client ID.
        
        Args:
            websocket: The WebSocket connection
            user_agent: Optional user agent string
            ip_address: Optional client IP address
            
        Returns:
            str: Unique client ID for this connection
            
        Raises:
            ConnectionError: If maximum connections exceeded
        """
        # Check connection limit
        if len(self.active_connections) >= self.max_connections:
            logger.warning(f"Connection limit exceeded. Current: {len(self.active_connections)}, Max: {self.max_connections}")
            raise ConnectionError("Maximum connections exceeded")
        
        client_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # Store connection
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = ConnectionInfo(
            client_id=client_id,
            connected_at=current_time,
            last_activity=current_time,
            message_count=0,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Initialize message queue for this client
        self._message_queue[client_id] = []
        
        # Update statistics
        self._stats["total_connections"] += 1
        
        logger.info(f"WebSocket client {client_id} connected. Total connections: {len(self.active_connections)}")
        
        # Start background tasks if this is the first connection
        if len(self.active_connections) == 1:
            await self._start_background_tasks()
        
        return client_id
    
    def disconnect(self, client_id: str):
        """
        Remove a WebSocket connection and cleanup resources.
        
        Args:
            client_id: The client ID to disconnect
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        if client_id in self.connection_info:
            connection_info = self.connection_info[client_id]
            connection_time = datetime.now() - connection_info.connected_at
            
            logger.info(
                f"WebSocket client {client_id} disconnected. "
                f"Connection duration: {connection_time}, Messages: {connection_info.message_count}. "
                f"Remaining connections: {len(self.active_connections)}"
            )
            
            del self.connection_info[client_id]
        
        # Clean up message queue
        if client_id in self._message_queue:
            del self._message_queue[client_id]
        
        # Stop background tasks if no connections remain
        if len(self.active_connections) == 0:
            asyncio.create_task(self._stop_background_tasks())
    
    async def disconnect_all(self):
        """Disconnect all active WebSocket connections."""
        logger.info(f"Disconnecting all {len(self.active_connections)} WebSocket connections")
        
        # Stop background tasks first
        await self._stop_background_tasks()
        
        # Close all connections
        for client_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket for client {client_id}: {str(e)}")
        
        # Clear all connections and metadata
        self.active_connections.clear()
        self.connection_info.clear()
        self._message_queue.clear()
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str, retry: bool = True) -> bool:
        """
        Send a message to a specific client with retry logic.
        
        Args:
            message: The message to send
            client_id: The target client ID
            retry: Whether to retry failed messages
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if client_id not in self.active_connections:
            logger.warning(f"Attempted to send message to non-existent client {client_id}")
            return False
        
        # Create structured message
        ws_message = WebSocketMessage(
            type=message.get("type", "unknown"),
            data=message.get("data"),
            message=message.get("message"),
            client_id=client_id
        )
        
        try:
            websocket = self.active_connections[client_id]
            
            # Check if WebSocket is still connected before sending
            if websocket.client_state.name != "CONNECTED":
                logger.debug(f"WebSocket for client {client_id} is not connected (state: {websocket.client_state.name})")
                self.disconnect(client_id)
                return False
                
            await websocket.send_json(ws_message.to_dict())
            
            # Update connection info
            if client_id in self.connection_info:
                self.connection_info[client_id].last_activity = datetime.now()
                self.connection_info[client_id].message_count += 1
            
            # Update statistics
            self._stats["messages_sent"] += 1
            
            return True
            
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected during message send")
            self.disconnect(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {str(e)}")
            self._stats["messages_failed"] += 1
            
            # Queue message for retry if enabled
            if retry and client_id in self._message_queue:
                self._message_queue[client_id].append(ws_message)
                logger.debug(f"Queued message for retry to client {client_id}")
            
            # Remove the problematic connection
            self.disconnect(client_id)
            return False
    
    async def broadcast(self, message: Dict[str, Any], exclude_client: str = None) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast
            exclude_client: Optional client ID to exclude from broadcast
            
        Returns:
            int: Number of clients that received the message successfully
        """
        if not self.active_connections:
            logger.debug("No active connections for broadcast")
            return 0
        
        target_clients = [
            client_id for client_id in self.active_connections.keys()
            if client_id != exclude_client
        ]
        
        if not target_clients:
            logger.debug("No target clients for broadcast after exclusions")
            return 0
        
        logger.info(f"Broadcasting message to {len(target_clients)} clients")
        
        # Create structured message
        ws_message = WebSocketMessage(
            type=message.get("type", "broadcast"),
            data=message.get("data"),
            message=message.get("message")
        )
        
        # Send to all target connections
        successful_sends = 0
        disconnected_clients = []
        
        for client_id in target_clients:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(ws_message.to_dict())
                
                # Update connection info
                if client_id in self.connection_info:
                    self.connection_info[client_id].last_activity = datetime.now()
                    self.connection_info[client_id].message_count += 1
                
                successful_sends += 1
                
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected during broadcast")
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {str(e)}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
        
        # Update statistics
        self._stats["broadcasts_sent"] += 1
        self._stats["messages_sent"] += successful_sends
        self._stats["messages_failed"] += len(disconnected_clients)
        
        logger.info(f"Broadcast completed: {successful_sends} successful, {len(disconnected_clients)} failed")
        return successful_sends
    
    async def broadcast_to_subset(self, message: Dict[str, Any], client_ids: Set[str]):
        """
        Broadcast a message to a specific subset of clients.
        
        Args:
            message: The message to broadcast
            client_ids: Set of client IDs to send to
        """
        if not client_ids:
            return
        
        logger.info(f"Broadcasting message to {len(client_ids)} specific clients")
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        disconnected_clients = []
        
        for client_id in client_ids:
            if client_id not in self.active_connections:
                logger.warning(f"Client {client_id} not in active connections")
                continue
                
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message)
                
                # Update metadata
                if client_id in self.connection_metadata:
                    self.connection_metadata[client_id]["last_activity"] = datetime.now()
                    self.connection_metadata[client_id]["message_count"] += 1
                    
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {str(e)}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about all active connections."""
        info = {
            "total_connections": len(self.active_connections),
            "max_connections": self.max_connections,
            "connections": {},
            "statistics": self.get_statistics()
        }
        
        for client_id, conn_info in self.connection_info.items():
            info["connections"][client_id] = conn_info.to_dict()
        
        return info
    
    async def ping_all_clients(self):
        """Send ping to all clients to check connection health."""
        if not self.active_connections:
            return
        
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        
        await self.broadcast(ping_message)
    
    async def send_status_update(self, status: str, message: str = None, data: Dict[str, Any] = None, 
                               client_id: str = None) -> bool:
        """
        Send a real-time status update to clients.
        
        Args:
            status: Status type (e.g., 'processing', 'completed', 'error')
            message: Optional status message
            data: Optional additional data
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        status_message = {
            "type": MessageType.STATUS_UPDATE,
            "data": {
                "status": status,
                "message": message,
                "details": data or {}
            }
        }
        
        if client_id:
            return await self.send_personal_message(status_message, client_id)
        else:
            successful_sends = await self.broadcast(status_message)
            return successful_sends > 0
    
    async def send_agent_response(self, agent_name: str, response_data: Dict[str, Any], 
                                client_id: str = None) -> bool:
        """
        Send an agent response update to clients.
        
        Args:
            agent_name: Name of the agent that responded
            response_data: Agent response data
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        agent_message = {
            "type": MessageType.AGENT_RESPONSE,
            "data": {
                "agent_name": agent_name,
                "response": response_data
            }
        }
        
        if client_id:
            return await self.send_personal_message(agent_message, client_id)
        else:
            successful_sends = await self.broadcast(agent_message)
            return successful_sends > 0
    
    async def send_error(self, error_message: str, error_code: str = None, 
                        client_id: str = None) -> bool:
        """
        Send an error message to clients.
        
        Args:
            error_message: Error message
            error_code: Optional error code
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        error_msg = {
            "type": MessageType.ERROR,
            "message": error_message,
            "data": {
                "error_code": error_code
            } if error_code else None
        }
        
        if client_id:
            return await self.send_personal_message(error_msg, client_id)
        else:
            successful_sends = await self.broadcast(error_msg)
            return successful_sends > 0
    
    async def send_agent_status_update(self, agent_name: str, status: str, progress: int = 0,
                                     message: str = None, trace: List[Dict[str, Any]] = None,
                                     metadata: Dict[str, Any] = None, client_id: str = None) -> bool:
        """
        Send detailed agent status update to clients.
        
        Args:
            agent_name: Name of the agent
            status: Current status (initializing, running, completed, failed)
            progress: Progress percentage (0-100)
            message: Optional status message
            trace: Optional list of execution trace entries
            metadata: Optional additional metadata
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        status_data = {
            "agent_name": agent_name,
            "status": status,
            "progress": progress,
            "message": message or f"Agent {agent_name} is {status}",
            "trace": trace or [],
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        agent_status_msg = {
            "type": MessageType.AGENT_STATUS,
            "data": status_data
        }
        
        if client_id:
            return await self.send_personal_message(agent_status_msg, client_id)
        else:
            successful_sends = await self.broadcast(agent_status_msg)
            return successful_sends > 0
    
    async def send_agent_step_update(self, agent_name: str, step_type: str, step_data: Dict[str, Any],
                                   client_id: str = None) -> bool:
        """
        Send agent step execution update to clients.
        
        Args:
            agent_name: Name of the agent
            step_type: Type of step (tool_call, analysis, synthesis, etc.)
            step_data: Data about the step
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        step_update = {
            "type": MessageType.AGENT_STEP,
            "data": {
                "agent_name": agent_name,
                "step_type": step_type,
                "step_data": step_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if client_id:
            return await self.send_personal_message(step_update, client_id)
        else:
            successful_sends = await self.broadcast(step_update)
            return successful_sends > 0
    
    async def send_tool_call_update(self, agent_name: str, tool_name: str, tool_status: str,
                                  tool_data: Dict[str, Any] = None, client_id: str = None) -> bool:
        """
        Send tool call update to clients.
        
        Args:
            agent_name: Name of the agent making the tool call
            tool_name: Name of the tool being called
            tool_status: Status of the tool call (started, completed, failed)
            tool_data: Optional data about the tool call
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        tool_update = {
            "type": MessageType.TOOL_CALL,
            "data": {
                "agent_name": agent_name,
                "tool_name": tool_name,
                "status": tool_status,
                "tool_data": tool_data or {},
                "timestamp": datetime.now().isoformat()
            }
        }
        
        if client_id:
            return await self.send_personal_message(tool_update, client_id)
        else:
            successful_sends = await self.broadcast(tool_update)
            return successful_sends > 0
    
    async def send_query_analysis_update(self, analysis_data: Dict[str, Any], client_id: str = None) -> bool:
        """
        Send query analysis results to clients.
        
        Args:
            analysis_data: Query analysis results
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        analysis_update = {
            "type": MessageType.QUERY_ANALYSIS,
            "data": analysis_data,
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            return await self.send_personal_message(analysis_update, client_id)
        else:
            successful_sends = await self.broadcast(analysis_update)
            return successful_sends > 0
    
    async def send_final_recommendation_update(self, recommendation_data: Dict[str, Any], 
                                             client_id: str = None) -> bool:
        """
        Send final recommendation to clients.
        
        Args:
            recommendation_data: Final recommendation data
            client_id: If specified, send only to this client; otherwise broadcast
            
        Returns:
            bool: True if sent successfully
        """
        recommendation_update = {
            "type": MessageType.FINAL_RECOMMENDATION,
            "data": recommendation_data,
            "message": "Analysis completed successfully",
            "timestamp": datetime.now().isoformat()
        }
        
        if client_id:
            return await self.send_personal_message(recommendation_update, client_id)
        else:
            successful_sends = await self.broadcast(recommendation_update)
            return successful_sends > 0
    
    def register_message_handler(self, message_type: str, handler: Callable):
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: The message type to handle
            handler: Async function to handle the message
        """
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def handle_message(self, message: Dict[str, Any], client_id: str) -> bool:
        """
        Handle an incoming message using registered handlers.
        
        Args:
            message: The received message
            client_id: ID of the client that sent the message
            
        Returns:
            bool: True if message was handled successfully
        """
        message_type = message.get("type")
        
        if message_type in self.message_handlers:
            try:
                handler = self.message_handlers[message_type]
                await handler(message, client_id)
                return True
            except Exception as e:
                logger.error(f"Error handling message type {message_type}: {str(e)}")
                await self.send_error(f"Error processing {message_type}", client_id=client_id)
                return False
        else:
            logger.warning(f"No handler registered for message type: {message_type}")
            await self.send_error(f"Unknown message type: {message_type}", client_id=client_id)
            return False
    
    async def _start_background_tasks(self):
        """Start background tasks for connection management."""
        logger.info("Starting WebSocket background tasks")
        
        # Ping task
        ping_task = asyncio.create_task(self._ping_loop())
        self._background_tasks.add(ping_task)
        ping_task.add_done_callback(self._background_tasks.discard)
        
        # Cleanup task
        cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._background_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self._background_tasks.discard)
    
    async def _stop_background_tasks(self):
        """Stop all background tasks."""
        logger.info("Stopping WebSocket background tasks")
        
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        self._background_tasks.clear()
    
    async def _ping_loop(self):
        """Background task to ping all clients periodically."""
        while True:
            try:
                await asyncio.sleep(self.ping_interval)
                if self.active_connections:
                    await self.ping_all_clients()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ping loop: {str(e)}")
    
    async def _cleanup_loop(self):
        """Background task to clean up stale connections."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self.cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
    
    async def cleanup_stale_connections(self, max_idle_minutes: int = 30):
        """
        Clean up connections that have been idle for too long.
        
        Args:
            max_idle_minutes: Maximum idle time in minutes before cleanup
        """
        if not self.connection_info:
            return
        
        current_time = datetime.now()
        stale_clients = []
        
        for client_id, conn_info in self.connection_info.items():
            idle_time = current_time - conn_info.last_activity
            if idle_time.total_seconds() > (max_idle_minutes * 60):
                stale_clients.append(client_id)
        
        if stale_clients:
            logger.info(f"Cleaning up {len(stale_clients)} stale connections")
            
            for client_id in stale_clients:
                try:
                    if client_id in self.active_connections:
                        await self.active_connections[client_id].close()
                except Exception as e:
                    logger.warning(f"Error closing stale connection {client_id}: {str(e)}")
                finally:
                    self.disconnect(client_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            **self._stats,
            "active_connections": len(self.active_connections),
            "queued_messages": sum(len(queue) for queue in self._message_queue.values()),
            "background_tasks": len(self._background_tasks)
        }