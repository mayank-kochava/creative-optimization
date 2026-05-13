'use client';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import { ConfigProvider } from 'antd';

export default function AntdProviders({ children }: { children: React.ReactNode }) {
  return (
    <AntdRegistry>
      <ConfigProvider theme={{ token: { colorPrimary: '#1677ff', borderRadius: 6 } }}>
        {children}
      </ConfigProvider>
    </AntdRegistry>
  );
}
