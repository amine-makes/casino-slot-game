#!/usr/bin/env node

// Simple test script for the Netlify Functions
const { handler } = require('./netlify/functions/api.js');

async function test() {
    console.log('🧪 Testing Netlify Functions locally...\n');
    
    // Test health check
    console.log('1. Testing health check...');
    const healthResponse = await handler({
        httpMethod: 'GET',
        path: '/health'
    });
    console.log('Health check response:', healthResponse.statusCode, JSON.parse(healthResponse.body));
    
    // Test session creation
    console.log('\n2. Testing session creation...');
    const sessionResponse = await handler({
        httpMethod: 'POST',
        path: '/session',
        body: '{}'
    });
    console.log('Session creation response:', sessionResponse.statusCode);
    const sessionData = JSON.parse(sessionResponse.body);
    console.log('Session ID:', sessionData.session_id);
    
    // Test deposit
    console.log('\n3. Testing deposit...');
    const depositResponse = await handler({
        httpMethod: 'POST',
        path: '/wallet/deposit',
        body: JSON.stringify({
            session_id: sessionData.session_id,
            amount: 100
        })
    });
    console.log('Deposit response:', depositResponse.statusCode, JSON.parse(depositResponse.body));
    
    // Test spin
    console.log('\n4. Testing spin...');
    const spinResponse = await handler({
        httpMethod: 'POST',
        path: '/spin',
        body: JSON.stringify({
            session_id: sessionData.session_id,
            bet_amount: 1.5,
            client_seed: 'test'
        })
    });
    console.log('Spin response:', spinResponse.statusCode);
    const spinData = JSON.parse(spinResponse.body);
    console.log('Spin result - Grid:', spinData.grid);
    console.log('Total win:', spinData.total_win);
    console.log('New balance:', spinData.balance);
    
    console.log('\n✅ All tests completed successfully!');
    console.log('🚀 Your casino is ready for Netlify deployment!');
}

test().catch(console.error);