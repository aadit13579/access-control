import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

type User = {
  id: number;
  name: string;
  kind: string;
  client_id: number | null;
};

type RolePermission = {
  role_code: string;
  permissions: string[];
};

type PermissionsResponse = {
  user_id: number;
  roles: RolePermission[];
  permissions: string[];
};

type UserContextType = {
  users: User[];
  currentUser: User | undefined;
  currentUserId: number | null;
  setCurrentUserId: (id: number) => void;

  roles: RolePermission[];
  permissions: string[];
};

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUserId, setCurrentUserId] =
    useState<number | null>(null);

  const [roles, setRoles] = useState<RolePermission[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  // Load users once
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/users`)
      .then((response) => response.json())
      .then((result) => {
        setUsers(result.data);

        if (result.data.length > 0) {
          setCurrentUserId(result.data[0].id);
        }
      });
  }, [API_BASE_URL]);

  // Load permissions whenever selected user changes
  useEffect(() => {
    if (currentUserId === null) {
      return;
    }

    fetch(
      `${API_BASE_URL}/api/users/${currentUserId}/permissions`
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load permissions');
        }

        return response.json();
      })
      .then((result: PermissionsResponse) => {
        setRoles(result.roles);
        setPermissions(result.permissions);
      })
      .catch(() => {
        setRoles([]);
        setPermissions([]);
      });
  }, [currentUserId, API_BASE_URL]);

  const currentUser = users.find(
    (user) => user.id === currentUserId
  );

  return (
    <UserContext.Provider
      value={{
        users,
        currentUser,
        currentUserId,
        setCurrentUserId,
        roles,
        permissions,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);

  if (!context) {
    throw new Error('useUser must be used inside UserProvider');
  }

  return context;
}