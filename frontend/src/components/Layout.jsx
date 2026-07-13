import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import NotificationsPanel from './NotificationsPanel';
import { styled } from '../stitches.config';
import { Search, Bell, HelpCircle, LogOut } from 'lucide-react';

const LayoutWrapper = styled('div', {
  minHeight: '100vh',
  color: '$textPrimary',
  fontFamily: '$base',
  backgroundColor: '$bg',
  display: 'flex',
});

const Sidebar = styled('aside', {
  height: '100vh',
  width: '256px',
  position: 'fixed',
  left: 0,
  top: 0,
  display: 'flex',
  flexDirection: 'column',
  zIndex: 50,
  background: '$surface',
  backdropFilter: 'blur(24px)',
  borderRight: '1px solid $border',
  paddingTop: '$5',
});

const SidebarHeader = styled('div', {
  padding: '0 $5',
  marginBottom: '48px',
});

const BrandTitle = styled('h1', {
  fontSize: '$headlineMd',
  fontWeight: '900',
  color: '$accent',
  letterSpacing: '-0.02em',
});

const BrandSubtitle = styled('p', {
  fontSize: '10px',
  color: '$textSecondary',
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  fontWeight: '600',
  marginTop: '4px',
});

const Nav = styled('nav', {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
});

const NavItem = styled(Link, {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '14px $5',
  color: '$textSecondary',
  textDecoration: 'none',
  transition: '$base',
  borderLeft: '4px solid transparent',
  '&:hover': {
    color: '$accent',
    background: 'rgba(255, 255, 255, 0.03)',
  },
  variants: {
    active: {
      true: {
        color: '$accent',
        background: '$accentGlow',
        borderLeftColor: '$accent',
      }
    }
  }
});

const NavIcon = styled('span', {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
});

const NavText = styled('span', {
  fontSize: '$bodySm',
  fontWeight: '600',
});

const SidebarFooter = styled('div', {
  padding: '$5',
  marginTop: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: '24px',
});

const PrimaryButton = styled('button', {
  width: '100%',
  background: '$accent',
  color: '$bg',
  fontWeight: '700',
  fontSize: '$bodySm',
  padding: '14px',
  borderRadius: '$xl',
  border: 'none',
  cursor: 'pointer',
  transition: '$base',
  boxShadow: '$glow',
  '&:hover': {
    background: '$accentHover',
    transform: 'translateY(-2px)',
    boxShadow: '0 6px 20px rgba(173, 198, 255, 0.4)',
  },
  '&:active': {
    transform: 'scale(0.95)',
  }
});

const FooterLinks = styled('div', {
  paddingTop: '24px',
  borderTop: '1px solid $border',
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
});

const FooterLink = styled('button', {
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  color: '$textSecondary',
  padding: '10px 0',
  background: 'transparent',
  border: 'none',
  cursor: 'pointer',
  transition: '$base',
  fontSize: '$bodySm',
  '&:hover': {
    color: '$textPrimary',
  },
  variants: {
    danger: {
      true: {
        color: '$danger',
        '&:hover': {
          color: '#ffdad6',
        }
      }
    }
  }
});

const MainArea = styled('main', {
  marginLeft: '256px',
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  flex: 1,
});

const Header = styled('header', {
  width: '100%',
  height: '80px',
  position: 'sticky',
  top: 0,
  zIndex: 40,
  background: '$surface',
  backdropFilter: 'blur(24px)',
  borderBottom: '1px solid $border',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 $5',
});

const SearchContainer = styled('div', {
  position: 'relative',
  width: '100%',
  maxWidth: '400px',
});

const SearchInput = styled('input', {
  width: '100%',
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid $border',
  borderRadius: '$round',
  padding: '10px 16px 10px 44px',
  color: '$textPrimary',
  fontSize: '$bodySm',
  transition: '$base',
  '&:focus': {
    outline: 'none',
    borderColor: '$accent',
    boxShadow: '0 0 0 1px $colors$accentGlow',
  },
  '&::placeholder': {
    color: '$textMuted',
  }
});

const SearchIconWrapper = styled('div', {
  position: 'absolute',
  left: '16px',
  top: '50%',
  transform: 'translateY(-50%)',
  color: '$textSecondary',
  pointerEvents: 'none',
});

const HeaderActions = styled('div', {
  display: 'flex',
  alignItems: 'center',
  gap: '32px',
});

const IconButton = styled('button', {
  background: 'transparent',
  border: 'none',
  color: '$textSecondary',
  cursor: 'pointer',
  position: 'relative',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: '$base',
  '&:hover': {
    color: '$accent',
  }
});

const NotificationBadge = styled('div', {
  position: 'absolute',
  top: '0',
  right: '0',
  width: '8px',
  height: '8px',
  background: '$accent',
  borderRadius: '$round',
  border: '2px solid $bg',
});

const Divider = styled('div', {
  height: '40px',
  width: '1px',
  background: '$border',
});

const UserProfile = styled('div', {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
});

const UserInfo = styled('div', {
  textAlign: 'right',
  display: 'none',
  '@media (min-width: 640px)': {
    display: 'block',
  }
});

const UserName = styled('p', {
  fontSize: '$bodySm',
  fontWeight: '700',
  color: '$textPrimary',
  lineHeight: '1.2',
});

const UserRole = styled('p', {
  fontSize: '10px',
  color: '$textSecondary',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
});

const AvatarWrapper = styled('div', {
  width: '40px',
  height: '40px',
  borderRadius: '$round',
  border: '2px solid rgba(255, 255, 255, 0.1)',
  padding: '2px',
  overflow: 'hidden',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: '$surface',
});

const AvatarImg = styled('img', {
  width: '100%',
  height: '100%',
  objectFit: 'cover',
  borderRadius: '$round',
});

const ContentArea = styled('div', {
  flex: 1,
});

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const userRole = localStorage.getItem('userRole') || 'Systems Arch';
  
  const navItems = [
    { path: '/', label: 'Dashboard', icon: <Search size={22} /> },
  ];

  if (['Admin', 'Investigator', 'Supervisor'].includes(userRole)) {
    navItems.push({ path: '/claims', label: 'Claims', icon: <Search size={22} /> }); // Placeholder icons
    navItems.push({ path: '/investigations', label: 'Investigations', icon: <Search size={22} /> });
  }
  
  if (['Admin'].includes(userRole)) {
    navItems.push({ path: '/admin/model-health', label: 'Model Health', icon: <Search size={22} /> });
  }

  if (['Admin', 'Officer'].includes(userRole)) {
    navItems.push({ path: '/upload', label: 'Upload Claims', icon: <Search size={22} /> });
  }

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  return (
    <LayoutWrapper>
      <Sidebar>
        <SidebarHeader>
          <BrandTitle>Aegis</BrandTitle>
          <BrandSubtitle>Admin Console</BrandSubtitle>
        </SidebarHeader>
        
        <Nav>
          {navItems.map((item) => (
            <NavItem 
              key={item.path} 
              to={item.path} 
              active={location.pathname === item.path}
            >
              <NavIcon>{item.icon}</NavIcon>
              <NavText>{item.label}</NavText>
            </NavItem>
          ))}
        </Nav>
        
        <SidebarFooter>
          <PrimaryButton>New Report</PrimaryButton>
          <FooterLinks>
            <FooterLink>
              <HelpCircle size={20} />
              Support
            </FooterLink>
            <FooterLink danger onClick={handleLogout}>
              <LogOut size={20} />
              Log Out
            </FooterLink>
          </FooterLinks>
        </SidebarFooter>
      </Sidebar>

      <MainArea>
        <Header>
          <div style={{ flex: 1 }}>
            <SearchContainer>
              <SearchIconWrapper><Search size={20} /></SearchIconWrapper>
              <SearchInput placeholder="Search system resources..." />
            </SearchContainer>
          </div>
          
          <HeaderActions>
            <IconButton>
              <Bell size={24} />
              <NotificationBadge />
            </IconButton>
            <IconButton>
              <HelpCircle size={24} />
            </IconButton>
            
            <Divider />
            
            <UserProfile>
              <UserInfo>
                <UserName>Alex Rivera</UserName>
                <UserRole>{userRole}</UserRole>
              </UserInfo>
              <AvatarWrapper>
                <AvatarImg src="https://lh3.googleusercontent.com/aida-public/AB6AXuCjqZkqV7fim-CeNI-3voiVxyLfllMedVl8CsJHvltbj1Tth5AXLuvG3caSZOId6GBIiEp3PdA0UfyJfZ9bw6nhvRjfTtziEu1L5hly8_CBjhecauQyorCTvR2dulXYZoM4IFV_bqSyH6Ght1_5dgdxgfWjMEzArhaonLK1BHv1eGFaMjdkwaXMskYRlFp_bacE2n__B24tgcV5ODrs_6Ws-BLzMbwdL1_urAekYHSXddv0rkVC-SXM" alt="User Avatar" />
              </AvatarWrapper>
            </UserProfile>
          </HeaderActions>
        </Header>
        
        <ContentArea>
          {children}
        </ContentArea>
      </MainArea>
    </LayoutWrapper>
  );
};

export default Layout;
