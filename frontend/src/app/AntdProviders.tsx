'use client';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import { ConfigProvider, Layout, Typography } from 'antd';

const { Header, Content } = Layout;
const { Title } = Typography;

export default function AntdProviders({ children }: { children: React.ReactNode }) {
  return (
    <AntdRegistry>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
          },
        }}
      >
        <Layout style={{ minHeight: '100vh' }}>
          <Header style={{ display: 'flex', alignItems: 'center', background: '#001529' }}>
            <Title level={4} style={{ color: 'white', margin: 0 }}>
              Creative Intelligence Platform
            </Title>
          </Header>
          <Content style={{ padding: '24px' }}>
            {children}
          </Content>
        </Layout>
      </ConfigProvider>
    </AntdRegistry>
  );
}
