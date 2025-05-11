"""
ML Orchestrator Authentication Scheme Pattern

This example demonstrates the authentication patterns used in the ML Orchestrator
for securing API endpoints and validating service-to-service communication.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, cast

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, validator

# Authentication configuration
JWT_SECRET = "this_would_be_loaded_from_environment_in_production"
JWT_ALGORITHM = "HS256"
API_KEY_HEADER_NAME = "X-API-Key"

# Authentication models
class UserRole(str, Enum):
    """User roles for role-based access control."""
    ADMIN = "admin"
    USER = "user"
    SERVICE = "service"
    READ_ONLY = "read_only"


class TokenData(BaseModel):
    """Model representing JWT token claims."""
    sub: str = Field(..., description="Subject (user ID)")
    roles: List[UserRole] = Field(default_factory=list, description="User roles")
    service_name: Optional[str] = Field(None, description="Service name for service-to-service auth")
    exp: datetime = Field(..., description="Expiration timestamp")
    
    @validator("exp")
    def check_expiration(cls, exp: datetime) -> datetime:
        """Validate that the token has not expired."""
        if exp < datetime.utcnow():
            raise ValueError("Token has expired")
        return exp


class User(BaseModel):
    """Model representing an authenticated user."""
    user_id: str
    roles: List[UserRole] = Field(default_factory=list)
    service_name: Optional[str] = None
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return UserRole.ADMIN in self.roles
    
    @property
    def is_service(self) -> bool:
        """Check if authentication is for service-to-service communication."""
        return UserRole.SERVICE in self.roles
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role."""
        return role in self.roles


# Authentication handlers

class AuthHandler:
    """
    Authentication handler for ML Orchestrator.
    
    Features:
    - JWT token generation and validation
    - API key validation for service-to-service auth
    - Role-based access control
    - FastAPI security dependencies
    """
    
    # FastAPI security schemes
    jwt_scheme = HTTPBearer(auto_error=False)
    api_key_scheme = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)
    
    # API key storage (in production, this would be in a database)
    _api_keys: Dict[str, Dict[str, Union[str, List[str]]]] = {
        "service1_key": {
            "service_name": "model-registry",
            "roles": [UserRole.SERVICE]
        },
        "service2_key": {
            "service_name": "inference-service",
            "roles": [UserRole.SERVICE]
        }
    }
    
    @classmethod
    def create_jwt_token(
        cls, 
        user_id: str, 
        roles: List[UserRole], 
        service_name: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT token.
        
        Args:
            user_id: User identifier
            roles: List of user roles
            service_name: Optional service name for service tokens
            expires_delta: Optional expiration time delta (defaults to 1 hour)
            
        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=1)
            
        expires_at = datetime.utcnow() + expires_delta
        
        payload = {
            "sub": user_id,
            "roles": [role.value for role in roles],
            "exp": expires_at
        }
        
        if service_name:
            payload["service_name"] = service_name
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @classmethod
    def decode_jwt_token(cls, token: str) -> TokenData:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData object with validated claims
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Convert role strings back to UserRole enum
            roles = [UserRole(role) for role in payload.get("roles", [])]
            
            return TokenData(
                sub=payload["sub"],
                roles=roles,
                service_name=payload.get("service_name"),
                exp=datetime.fromtimestamp(payload["exp"])
            )
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    @classmethod
    def validate_api_key(cls, api_key: str) -> User:
        """
        Validate an API key and return associated user/service.
        
        Args:
            api_key: API key string
            
        Returns:
            User object with service information
            
        Raises:
            HTTPException: If API key is invalid
        """
        service_info = cls._api_keys.get(api_key)
        if not service_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
            
        service_name = cast(str, service_info["service_name"])
        roles = [UserRole(role) for role in service_info.get("roles", [])]
        
        return User(
            user_id=f"service:{service_name}",
            roles=roles,
            service_name=service_name
        )

    @classmethod
    async def get_current_user(
        cls,
        request: Request,
        token: Optional[HTTPAuthorizationCredentials] = Security(jwt_scheme),
        api_key: Optional[str] = Security(api_key_scheme)
    ) -> User:
        """
        FastAPI dependency for getting the current authenticated user.
        Supports both JWT and API key authentication.
        
        Args:
            request: FastAPI request object
            token: Optional JWT token from Authorization header
            api_key: Optional API key from X-API-Key header
            
        Returns:
            Authenticated User object
            
        Raises:
            HTTPException: If authentication fails
        """
        # Check if we have a JWT token
        if token and token.credentials:
            token_data = cls.decode_jwt_token(token.credentials)
            return User(
                user_id=token_data.sub,
                roles=token_data.roles,
                service_name=token_data.service_name
            )
            
        # Check if we have an API key
        if api_key:
            return cls.validate_api_key(api_key)
            
        # No valid authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    @classmethod
    def requires_roles(cls, required_roles: List[UserRole]):
        """
        Dependency factory for role-based access control.
        
        Args:
            required_roles: List of roles required to access the endpoint
            
        Returns:
            FastAPI dependency function that checks user roles
        """
        async def dependency(user: User = Depends(cls.get_current_user)) -> User:
            for role in required_roles:
                if user.has_role(role):
                    return user
                    
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
                
        return dependency
    
    @classmethod
    def admin_only(cls):
        """Dependency that requires admin role."""
        return cls.requires_roles([UserRole.ADMIN])
    
    @classmethod
    def service_only(cls):
        """Dependency that requires service role."""
        return cls.requires_roles([UserRole.SERVICE])


# Example usage with FastAPI

"""
from fastapi import APIRouter, Depends, FastAPI

app = FastAPI()

# 1. Define protected routes
router = APIRouter(prefix="/api/models")

@router.get("/")
async def list_models(user: User = Depends(AuthHandler.get_current_user)):
    # Any authenticated user can list models
    return {"models": ["model1", "model2"]}

@router.post("/")
async def create_model(user: User = Depends(AuthHandler.admin_only())):
    # Only admins can create models
    return {"status": "Model created"}

@router.get("/system-status")
async def get_system_status(user: User = Depends(AuthHandler.service_only())):
    # Only services can access system status
    return {"status": "healthy", "service": user.service_name}

app.include_router(router)
"""