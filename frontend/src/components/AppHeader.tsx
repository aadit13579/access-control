import { Link } from 'react-router-dom';

import {
  Header,
  HeaderName,
  HeaderNavigation,
  HeaderMenuItem,
  Dropdown,
} from '@carbon/react';

import { useUser } from '../context/UserContext';

export function AppHeader() {
  const {
  users,
  currentUser,
  setCurrentUserId,
  permissions,
} = useUser();

  const canManageGrants = permissions.includes('manage_grants');
  return (
    <Header aria-label="Access Control Service">
      <HeaderName as={Link} to="/" prefix="">
        Access Control Service
      </HeaderName>

      <HeaderNavigation aria-label="Main navigation">
        <HeaderMenuItem as={Link} to="/jobs">
          Jobs
        </HeaderMenuItem>

        <HeaderMenuItem as={Link} to="/waiting">
          Waiting
        </HeaderMenuItem>

        <HeaderMenuItem as={Link} to="/authorization">
          Authorization
        </HeaderMenuItem>
        {canManageGrants && (
          <HeaderMenuItem as={Link} to="/grants">
            Grants
          </HeaderMenuItem>
        )}

      </HeaderNavigation>

      <div
        style={{
          marginLeft: 'auto',
          width: '220px',
          paddingRight: '1rem',
        }}
      >
        <Dropdown
          id="user-switcher"
          titleText=""
          label="Select user"
          items={users}
          itemToString={(item) => item?.name ?? ''}
          selectedItem={currentUser}
          onChange={({ selectedItem }) => {
            if (selectedItem) {
              setCurrentUserId(selectedItem.id);
            }
          }}
        />
      </div>
    </Header>
  );
}